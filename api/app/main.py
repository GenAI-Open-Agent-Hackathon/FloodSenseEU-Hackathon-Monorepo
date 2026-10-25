"""FloodSense EU API.

The UI and the demo call this service on host port 18000. It owns the public
contract (docs/GAMEPLAN.md) and proxies the run lifecycle to the agents
service at AGENTS_URL: http://agents:8100 under Compose, 127.0.0.1:8100 on the
host.

Run responses gain a ``contract`` object: a projection of the graph snapshot
onto ``contracts/schemas/floodsense.schema.json``. The graph payload stays
beside it. Fake, seed, cache, and replay answers are not relabelled live here;
the agents service sets ``served_from``.

GET  /health                      this service
GET  /config                      flags and lanes, from the agents
POST /runs                        start a run; returns when the graph pauses for human approval
GET  /runs/past                   earlier runs
GET  /runs/{id}                   run snapshot
GET  /runs/{id}/events            SSE trace stream (proxied as-is)
GET  /runs/{id}/approval          the approval payload (409 unless awaiting approval)
POST /runs/{id}/approval          {action: approve | edit | reject, edits?, reviewer_note?, reviewer?}
GET  /runs/{id}/citations         citation records + evidence + provenance
"""

from __future__ import annotations

import json
import os

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.project import project_run

AGENTS_URL = os.environ.get("AGENTS_URL", "http://127.0.0.1:8100").rstrip("/")
UI_ORIGINS = [
    o
    for o in os.environ.get("UI_ORIGINS", "http://localhost:15173,http://127.0.0.1:15173").split(
        ","
    )
    if o
]
TIMEOUT = httpx.Timeout(
    600.0, connect=5.0
)  # a run waits for the deep lane; the connect timeout stays short

app = FastAPI(title="FloodSense EU", version="0.4.0")
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
    """Add the schema projection on run payloads. Leave errors and lists alone."""
    if response.status_code >= 400 or path == "/runs/past" or path.endswith("/events"):
        return response
    if path != "/runs" and not path.startswith("/runs/"):
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


@app.get("/config")
async def config() -> Response:
    return await _forward("GET", "/config")


@app.post("/runs", status_code=201)
async def start_run(request: Request) -> Response:
    return await _forward("POST", "/runs", body=await request.json())


@app.get("/runs/past")
async def past_runs(limit: int = 50) -> Response:
    return await _forward("GET", "/runs/past", params={"limit": limit})


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> Response:
    return await _forward("GET", f"/runs/{run_id}")


@app.get("/runs/{run_id}/approval")
async def get_approval(run_id: str) -> Response:
    return await _forward("GET", f"/runs/{run_id}/approval")


@app.post("/runs/{run_id}/approval")
async def post_approval(run_id: str, request: Request) -> Response:
    return await _forward("POST", f"/runs/{run_id}/approval", body=await request.json())


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
