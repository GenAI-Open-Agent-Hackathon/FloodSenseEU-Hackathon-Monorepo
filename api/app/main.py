"""FloodSense EU API.

The UI and the demo call this service on host port 18000. It owns the public
contract (docs/GAMEPLAN.md) and proxies the run lifecycle to the agents
service at AGENTS_URL: http://agents:8100 under Compose, 127.0.0.1:8100 on the
host.

``POST /runs`` and ``GET /runs/{id}`` gain a ``contract`` object: a projection
of the graph snapshot onto ``contracts/schemas/floodsense.schema.json``.
The graph payload stays beside it. Approval and citation payloads are left
alone. Fake, seed, cache, and replay answers are not relabelled live here;
the agents service sets ``served_from``.

The semantic cache and labelled replay sit here, in front of the proxy, each
behind its flag (FF_SEMANTIC_CACHE, FF_CACHED_REPLAY; see app/cache.py). A
cached or replayed answer is labelled by the agents, never presented as live.
Rate limits are a later increment and slot in here too.

GET  /health                      this service
GET  /config                      flags and lanes, from the agents
POST /runs                        start a run; returns when the graph pauses for human approval
                                  (thread_id continues a conversation: short-term thread memory)
                                  200 + served_from cache: a repeat of a finished question (FF_SEMANTIC_CACHE)
                                  200 + served_from replay: the live run failed (FF_CACHED_REPLAY)
                                  {"fresh": true} skips the cache
GET  /runs/past                   earlier runs (?thread_id= for one conversation)
GET  /runs/{id}                   run snapshot
GET  /runs/{id}/replay            a recorded run, labelled replay
GET  /runs/{id}/events            SSE trace stream (proxied as-is)
GET  /runs/{id}/approval          the approval payload (409 unless awaiting approval)
POST /runs/{id}/approval          {action: approve | edit | reject, edits?, reviewer_note?, reviewer?}
GET  /runs/{id}/citations         citation records + evidence + provenance
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.cache import (
    DEFAULT_CUSTOMER,
    DEFAULT_EVENT,
    FLAGS_MEMO_S,
    AnswerCache,
    approved_by_a_person,
    is_follow_up,
)
from app.project import project_run

AGENTS_URL = os.environ.get("AGENTS_URL", "http://127.0.0.1:8100").rstrip("/")
UI_ORIGINS = [
    o
    for o in os.environ.get("UI_ORIGINS", "http://localhost:15173,http://127.0.0.1:15173").split(
        ","
    )
    if o
]
# Full run snapshots only. /runs/{id}/approval and /citations are thinner
# and must not grow a contract that fills missing citation URLs.
_RUN_SNAPSHOT = re.compile(r"^/runs/[^/]+$")

TIMEOUT = httpx.Timeout(
    600.0, connect=5.0
)  # a run waits for the deep lane; the connect timeout stays short

app = FastAPI(title="FloodSense EU", version="0.4.0")
cache = AnswerCache()
app.add_middleware(
    CORSMiddleware, allow_origins=UI_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"]
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "floodsense-api"}


async def _agents_request(
    method: str, path: str, body: dict | None = None, params: dict | None = None
) -> httpx.Response:
    """One async client for every proxied call. SSE uses its own stream below."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await client.request(method, f"{AGENTS_URL}{path}", json=body, params=params)


def _attach_contract(path: str, response: Response) -> Response:
    """Add the schema projection on POST /runs and GET /runs/{id} only."""
    if response.status_code >= 400:
        return response
    if path != "/runs" and _RUN_SNAPSHOT.match(path) is None:
        return response
    media = response.media_type or ""
    if "json" not in media:
        return response
    try:
        payload = json.loads(response.body)
    except json.JSONDecodeError:
        return response
    if not isinstance(payload, dict):
        return response
    projected = project_run(payload)
    if projected is None:
        return response
    payload["contract"] = projected
    return Response(
        content=json.dumps(payload),
        status_code=response.status_code,
        media_type="application/json",
    )


def _json_run(payload: dict, status_code: int) -> JSONResponse:
    """A cache or replay body. The same projection as a live run snapshot."""
    projected = project_run(payload)
    if projected is not None:
        payload["contract"] = projected
    return JSONResponse(payload, status_code=status_code)


async def _forward(
    method: str, path: str, body: dict | None = None, params: dict | None = None
) -> Response:
    try:
        r = await _agents_request(method, path, body=body, params=params)
    except httpx.HTTPError as e:
        raise HTTPException(503, f"agents service unreachable at {AGENTS_URL}: {type(e).__name__}")
    response = Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )
    return _attach_contract(path, response)


async def _agents_json(method: str, path: str, params: dict | None = None) -> tuple[int, Any]:
    """Call the agents and parse JSON. (503, None) when they cannot be reached."""
    try:
        r = await _agents_request(method, path, params=params)
    except httpx.HTTPError:
        return 503, None
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


async def _agents_config() -> dict | None:
    code, data = await _agents_json("GET", "/config")
    return data if code == 200 and isinstance(data, dict) else None


async def _flag_fingerprint() -> str | None:
    """The agents' flag fingerprint. None when /config cannot be read.

    The cache memos this. A fresh memo skips another /config call. The fetch
    is async, so it happens here and flags() only stores the result.
    """
    memo = cache._flags
    if memo is not None and time.monotonic() - memo[0] < FLAGS_MEMO_S:
        return memo[1]
    config = await _agents_config()
    return cache.flags(lambda: config)


async def _from_cache(body: dict) -> dict | None:
    """The original run for a repeat of a finished question, or None."""
    flags = await _flag_fingerprint()
    if flags is None:
        return None
    entry = cache.lookup(body, flags)
    if entry is None:
        return None
    code, run = await _agents_json("GET", f"/runs/{entry.run_id}")
    if code != 200 or not isinstance(run, dict):
        cache.drop(entry.run_id)  # the agents no longer hold it
        return None
    age = int(time.time() - entry.stored_at)
    run["cache"] = {
        "original_run_id": entry.run_id,
        "age_s": age,
        "expires_in_s": max(0, int(entry.ttl_s - age)),
    }
    return run


def _live_failure(resp: Response) -> str | None:
    """Why the live run failed, or None when it did not."""
    if resp.status_code >= 500:
        return f"the agents answered HTTP {resp.status_code}"
    if resp.status_code in (200, 201):
        try:
            run = json.loads(resp.body)
        except ValueError:
            return None
        if isinstance(run, dict) and run.get("status") == "failed":
            return f"the live run failed: {str(run.get('error') or 'no detail')[:200]}"
    return None


async def _replay_for(body: dict, reason: str) -> dict | None:
    """The newest recorded run for this event and customer that a person approved."""
    event = body.get("event_id") or DEFAULT_EVENT
    customer = body.get("customer_id") or DEFAULT_CUSTOMER
    replay = None
    code, past = await _agents_json("GET", "/runs/past", params={"limit": 200})
    rows = past.get("runs") if code == 200 and isinstance(past, dict) else None
    for row in rows or []:
        if (
            row.get("event_id") == event
            and row.get("customer_id") == customer
            and row.get("status") == "approved"
            and row.get("approval") in ("approved", "edited")
            and (row.get("thread_id") or row["run_id"]) == row["run_id"]
        ):
            c, run = await _agents_json("GET", f"/runs/{row['run_id']}/replay")
            if c == 200 and isinstance(run, dict):
                replay = run
                break
    if replay is None:  # the agents are down or hold no such run: the last one seen here
        replay = cache.recording(event, customer)
    if replay is None:
        return None
    replay["replay"] = {"original_run_id": replay.get("run_id"), "reason": reason}
    return replay


@app.get("/config")
async def config() -> Response:
    code, data = await _agents_json("GET", "/config")
    if code == 503 and data is None:
        raise HTTPException(503, f"agents service unreachable at {AGENTS_URL}")
    if code != 200 or not isinstance(data, dict):
        return await _forward("GET", "/config")
    data["api_cache"] = cache.stats()
    return JSONResponse(data)


@app.post("/runs", status_code=201)
async def start_run(request: Request) -> Response:
    body = await request.json()
    fresh = bool(body.pop("fresh", False)) if isinstance(body, dict) else False
    settings = cache.settings
    if settings.semantic_cache and not fresh and isinstance(body, dict):
        hit = await _from_cache(body)
        if hit is not None:
            return _json_run(hit, 200)
    try:
        resp = await _forward("POST", "/runs", body=body)
    except HTTPException as e:
        if settings.cached_replay and isinstance(body, dict):
            replay = await _replay_for(body, f"the agents could not be reached ({e.detail})")
            if replay is not None:
                return _json_run(replay, 200)
        raise
    if settings.cached_replay and isinstance(body, dict):
        reason = _live_failure(resp)
        if reason:
            replay = await _replay_for(body, reason)
            if replay is not None:
                return _json_run(replay, 200)
    return resp


@app.get("/runs/past")
async def past_runs(limit: int = 50, thread_id: str | None = None) -> Response:
    params: dict = {"limit": limit}
    if thread_id:
        params["thread_id"] = thread_id
    return await _forward("GET", "/runs/past", params=params)


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> Response:
    return await _forward("GET", f"/runs/{run_id}")


@app.get("/runs/{run_id}/approval")
async def get_approval(run_id: str) -> Response:
    return await _forward("GET", f"/runs/{run_id}/approval")


@app.post("/runs/{run_id}/approval")
async def post_approval(run_id: str, request: Request) -> Response:
    resp = await _forward("POST", f"/runs/{run_id}/approval", body=await request.json())
    settings = cache.settings
    if resp.status_code == 200 and (settings.semantic_cache or settings.cached_replay):
        try:
            run = json.loads(resp.body)
        except ValueError:
            return resp
        if settings.semantic_cache:
            flags = await _flag_fingerprint()
            if flags is not None:
                cache.remember(run, flags)
        if settings.cached_replay and approved_by_a_person(run) and not is_follow_up(run):
            code, replay = await _agents_json("GET", f"/runs/{run_id}/replay")
            if code == 200 and isinstance(replay, dict):
                cache.record(replay)
    return resp


@app.get("/runs/{run_id}/replay")
async def get_replay(run_id: str) -> Response:
    return await _forward("GET", f"/runs/{run_id}/replay")


@app.get("/runs/{run_id}/citations")
async def get_citations(run_id: str) -> Response:
    return await _forward("GET", f"/runs/{run_id}/citations")


@app.get("/runs/{run_id}/events")
async def events(run_id: str) -> StreamingResponse:
    async def gen():
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                async with client.stream("GET", f"{AGENTS_URL}/runs/{run_id}/events") as r:
                    if r.status_code != 200:
                        yield f'event: error\ndata: {{"status": {r.status_code}}}\n\n'
                        return
                    async for chunk in r.aiter_text():
                        yield chunk
        except httpx.HTTPError as e:
            yield f'event: error\ndata: {{"error": "agents service unreachable: {type(e).__name__}"}}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")
