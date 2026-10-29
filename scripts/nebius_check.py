"""Nebius Token Factory live check for FloodSense EU. Host side, stdlib only.

Proves that Token Factory answers the request NebiusClient
(agents/floodsense_agents/nightshift.py, LLM_BACKEND=nebius) sends, on both
lanes, before the app is switched over.

    python scripts/nebius_check.py
    python scripts/nebius_check.py --fast nvidia/<id> --deep nvidia/<id>
    python scripts/nebius_check.py --out nebius-check.md

Reads NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL_FAST and NEBIUS_MODEL_DEEP
from agents/.env. A non-empty environment variable overrides the file, and
--fast / --deep override both. Checks, in order:

  1. GET  /models            lists the NVIDIA ids and any embedding models.
                             A lane model that is not listed fails.
  2. POST /chat/completions  one tiny JSON reply per lane with NebiusClient's
                             body (temperature 0.1, JSON mode, no thinking
                             switch), not streamed, with the same 400
                             fallback when JSON mode is refused. Reports the
                             model that answered, latency, tokens,
                             finish_reason and whether the reply parses.
  3. the same request streamed (SSE), as the agents send it by default
     (LLM_STREAM=true).
  4. the same request with chat_template_kwargs.enable_thinking=false, the
     switch NightshiftClient sends and NebiusClient does not: shows whether
     Token Factory accepts it and whether it cuts completion tokens.

Each chat call is capped at --max-tokens (default 1024), so a run costs well
under a cent. The key is never printed: it is scrubbed from every reply.
Exit 0 when no required check fails (warnings included), 1 when one fails,
2 on a config error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = ROOT / "agents" / ".env"
# Same defaults as agents/floodsense_agents/settings.py
DEFAULT_BASE = "https://api.tokenfactory.nebius.com/v1"
DEFAULT_FAST = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
DEFAULT_DEEP = "nvidia/Nemotron-3.5-Super-VL"

SYSTEM = 'TASK: check\nReply with one JSON object only: {"ok": true, "lane": "<lane>"}.'

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"


@dataclass
class Config:
    key: str
    base: str
    fast: str
    deep: str
    cap: int
    timeout: float


@dataclass
class Row:
    check: str
    lane: str
    result: str
    detail: str


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_config(args: argparse.Namespace) -> tuple[Config | None, list[str]]:
    file = parse_env_file(Path(args.env))

    def get(name: str, default: str = "") -> str:
        return os.environ.get(name) or file.get(name) or default

    key = get("NEBIUS_API_KEY")
    if not key:
        return None, [
            f"NEBIUS_API_KEY is empty: put the Token Factory key in {args.env} (gitignored)."
        ]
    base = get("NEBIUS_BASE_URL", DEFAULT_BASE).rstrip("/")
    if not base.startswith("https://"):
        return None, ["NEBIUS_BASE_URL must start with https://."]
    return (
        Config(
            key=key,
            base=base,
            fast=args.fast or get("NEBIUS_MODEL_FAST", DEFAULT_FAST),
            deep=args.deep or get("NEBIUS_MODEL_DEEP", DEFAULT_DEEP),
            cap=args.max_tokens,
            timeout=args.timeout,
        ),
        [],
    )


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _scrub(text: str, key: str) -> str:
    return text.replace(key, "***") if key else text


def send(cfg: Config, method: str, path: str, body: dict | None = None) -> tuple[int, str, float]:
    """(HTTP status, scrubbed body, seconds). Status 0 is a network error."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        cfg.base + path, data=data, method=method, headers=_headers(cfg.key)
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout) as r:
            status, raw = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        status, raw = 0, f"network error: {e}"
    return status, _scrub(raw, cfg.key), time.monotonic() - t0


def chat_body(
    model: str, lane: str, cap: int, *, json_mode: bool = True, thinking_off: bool = False
) -> dict:
    """NebiusClient.complete's body; thinking_off adds NightshiftClient's switch."""
    body: dict = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Lane: {lane}. Return the JSON object now."},
        ],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if cap > 0:
        body["max_tokens"] = cap
    if thinking_off:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    return body


def first_json(text: str) -> dict | None:
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.S)
    for candidate in (t, t[t.find("{") : t.rfind("}") + 1] if "{" in t else ""):
        try:
            v = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(v, dict):
            return v
    return None


def call_chat(
    cfg: Config, model: str, lane: str, *, thinking_off: bool = False
) -> tuple[int, str, float, bool]:
    """Non-streamed call with NebiusClient's JSON-mode downgrade. Last item: downgraded."""
    body = chat_body(model, lane, cfg.cap, thinking_off=thinking_off)
    status, raw, secs = send(cfg, "POST", "/chat/completions", body)
    if status == 400 and "response_format" in raw:
        body.pop("response_format")
        status, raw, more = send(cfg, "POST", "/chat/completions", body)
        return status, raw, secs + more, True
    return status, raw, secs, False


def call_stream(cfg: Config, model: str, lane: str) -> dict:
    """Streamed call; the reply assembled the way stream_post does it."""
    out: dict = {
        "status": 0,
        "parts": [],
        "finish": None,
        "model": None,
        "usage": None,
        "reasoning": False,
    }
    body = {
        **chat_body(model, lane, cfg.cap),
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    for attempt in (1, 2):
        req = urllib.request.Request(
            cfg.base + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={**_headers(cfg.key), "Accept": "text/event-stream"},
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout) as r:
                out["status"] = r.status
                for raw_line in r:
                    line = raw_line.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if chunk.get("error"):
                        out["error"] = _scrub(str(chunk["error"]), cfg.key)[:300]
                        break
                    out["model"] = chunk.get("model") or out["model"]
                    out["usage"] = chunk.get("usage") or out["usage"]
                    for ch in chunk.get("choices") or []:
                        delta = ch.get("delta") or {}
                        if delta.get("content"):
                            out["parts"].append(delta["content"])
                        if delta.get("reasoning_content") or delta.get("reasoning"):
                            out["reasoning"] = True
                        out["finish"] = ch.get("finish_reason") or out["finish"]
        except urllib.error.HTTPError as e:
            raw = _scrub(e.read().decode("utf-8", "replace"), cfg.key)
            if attempt == 1 and e.code == 400 and "response_format" in raw:
                body.pop("response_format")
                continue
            out.update(status=e.code, error=raw[:300])
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            out["error"] = f"{type(e).__name__}: {e}"[:300]
        out["secs"] = time.monotonic() - t0
        return out
    return out


def _tokens(usage: dict | None) -> str:
    u = usage or {}
    return f"{u.get('prompt_tokens', '?')}/{u.get('completion_tokens', '?')}"


def check_lane(cfg: Config, lane: str, model: str, listed: list[str]) -> list[Row]:
    rows: list[Row] = []
    if listed and model not in listed:
        rows.append(Row("lane model listed", lane, FAIL, f"{model} is not in /models"))
    elif listed:
        rows.append(Row("lane model listed", lane, PASS, model))

    # 2. non-streamed, NebiusClient's body
    status, raw, secs, downgraded = call_chat(cfg, model, lane)
    base_completion = None
    if status != 200:
        rows.append(Row("chat", lane, FAIL, f"HTTP {status}: {raw[:300]}"))
    else:
        js = json.loads(raw)
        ch = (js.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        extra = sorted(k for k, v in msg.items() if k not in ("role", "content") and v)
        base_completion = (js.get("usage") or {}).get("completion_tokens")
        finish = ch.get("finish_reason")
        parsed = first_json(msg.get("content") or "") is not None
        notes = [
            f"{secs:.1f}s",
            f"answered by {js.get('model') or '?'}",
            f"tokens in/out {_tokens(js.get('usage'))}",
            f"finish {finish}",
            "JSON ok" if parsed else "JSON not parsed",
        ]
        if downgraded:
            notes.append("JSON mode refused (400), prompt carried JSON")
        if extra:
            notes.append("extra reply fields: " + ", ".join(extra))
        if finish == "length":
            result = WARN
            notes.append(
                f"cut at {cfg.cap} tokens: hidden reasoning likely, see the thinking-off row"
            )
        else:
            result = PASS if parsed else WARN
        rows.append(Row("chat", lane, result, "; ".join(notes)))

    # 3. streamed
    s = call_stream(cfg, model, lane)
    if s.get("error") or s["status"] != 200:
        rows.append(Row("chat streamed", lane, FAIL, f"HTTP {s['status']}: {s.get('error', '')}"))
    elif not (s["parts"] or s["finish"]):
        rows.append(Row("chat streamed", lane, FAIL, "stream closed without an answer"))
    else:
        parsed = first_json("".join(s["parts"])) is not None
        notes = [
            f"{s.get('secs', 0):.1f}s",
            f"answered by {s['model'] or '?'}",
            f"tokens in/out {_tokens(s['usage'])}",
            f"finish {s['finish']}",
            "JSON ok" if parsed else "JSON not parsed",
        ]
        if s["reasoning"]:
            notes.append("reasoning deltas seen")
        result = PASS if parsed and s["finish"] != "length" else WARN
        rows.append(Row("chat streamed", lane, result, "; ".join(notes)))

    # 4. thinking switch
    status, raw, secs, _ = call_chat(cfg, model, lane, thinking_off=True)
    if status == 200:
        used = (json.loads(raw).get("usage") or {}).get("completion_tokens")
        detail = f"accepted; completion tokens {used} vs {base_completion} without it"
        rows.append(Row("enable_thinking=false", lane, INFO, detail))
    elif status in (400, 422):
        detail = f"refused (HTTP {status}); NebiusClient is right not to send it"
        rows.append(Row("enable_thinking=false", lane, INFO, detail))
    else:
        rows.append(Row("enable_thinking=false", lane, WARN, f"HTTP {status}: {raw[:200]}"))
    return rows


def report(cfg: Config, rows: list[Row], listed: list[str]) -> str:
    def cell(s: str) -> str:
        return s.replace("|", "/").replace("\n", " ")

    nvidia = sorted(i for i in listed if "nvidia" in i.lower() or "nemotron" in i.lower())
    embed = sorted(i for i in listed if "embed" in i.lower())
    lines = [
        "# Nebius Token Factory check",
        "",
        f"- Base URL: `{cfg.base}`",
        f"- Fast lane: `{cfg.fast}`",
        f"- Deep lane: `{cfg.deep}`",
        f"- Cap per chat call: {cfg.cap} tokens",
        "",
        "| Check | Lane | Result | Detail |",
        "| --- | --- | --- | --- |",
        *(f"| {cell(r.check)} | {r.lane} | {r.result} | {cell(r.detail)} |" for r in rows),
        "",
        f"## NVIDIA models listed ({len(nvidia)} of {len(listed)})",
        "",
        *([f"- `{i}`" for i in nvidia] or ["- none"]),
        "",
        "## Embedding models listed",
        "",
        *([f"- `{i}`" for i in embed] or ["- none"]),
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--env", default=str(DEFAULT_ENV), help="env file to read (default agents/.env)")
    p.add_argument("--fast", help="fast-lane model id (overrides NEBIUS_MODEL_FAST)")
    p.add_argument("--deep", help="deep-lane model id (overrides NEBIUS_MODEL_DEEP)")
    p.add_argument("--max-tokens", type=int, default=1024, help="cap per chat call (default 1024)")
    p.add_argument("--timeout", type=float, default=120.0, help="seconds per call (default 120)")
    p.add_argument("--out", help="also write the markdown report to this file")
    args = p.parse_args(argv)

    cfg, problems = load_config(args)
    if cfg is None:
        for msg in problems:
            print(f"config: {msg}", file=sys.stderr)
        return 2

    rows: list[Row] = []
    status, raw, secs = send(cfg, "GET", "/models")
    listed: list[str] = []
    if status == 200:
        try:
            listed = [m.get("id", "") for m in json.loads(raw).get("data", [])]
        except (ValueError, AttributeError):
            pass
    if status != 200 or not listed:
        rows.append(Row("GET /models", "-", FAIL, f"HTTP {status}: {raw[:300]}"))
    else:
        rows.append(Row("GET /models", "-", PASS, f"{len(listed)} models in {secs:.1f}s"))

    if status not in (401, 403, 0):  # a bad key or no network fails every call the same way
        for lane, model in (("fast", cfg.fast), ("deep", cfg.deep)):
            rows.extend(check_lane(cfg, lane, model, listed))

    text = report(cfg, rows, listed)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 1 if any(r.result == FAIL for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
