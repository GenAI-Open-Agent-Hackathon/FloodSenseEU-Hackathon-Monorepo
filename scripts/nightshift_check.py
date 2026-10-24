"""Nightshift live check for FloodSense EU. Host side, stdlib only.

Proves that this machine's Meterless Nightshift runtime answers the same
request the agents client (agents/floodsense_agents/nightshift.py) sends,
on both lanes.

    py scripts/nightshift_check.py
    py scripts/nightshift_check.py --out nightshift-check.md

Reads the root .env (host URLs on 127.0.0.1, not agents/.env). A non-empty
environment variable overrides the file. MODEL_FAST and MODEL_DEEP are
Nightshift routing modes (meterless/fast, meterless/deep): Nightshift picks
the lane, and each reply names the model that answered. Checks, in order:

  1. GET  /models            MODEL_FAST and MODEL_DEEP are both listed.
  2. POST /chat/completions  one tiny JSON reply per lane, with the agents
                             client's body: temperature 0.1, thinking off,
                             JSON mode, and the same 400 fallback. A
                             concrete model id answered by another model is
                             a warning (pin not honoured), and so is fast
                             and deep answered by the same model.
  3. POST /embeddings        optional probe for the semantic cache. No
                             embedding model is reported, not failed.

Prints a markdown summary that is safe to paste into a PR. The runtime token
is never printed and is scrubbed from any error text the server returns.
Exit 0 when no required check fails (warnings included), 1 when one fails,
2 on a config error.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / ".env"
KEYS: tuple[str, ...] = (
    "METERLESS_BASE_URL",
    "METERLESS_RUNTIME_TOKEN",
    "METERLESS_APP",
    "METERLESS_SCOPE",
    "MODEL_FAST",
    "MODEL_DEEP",
    "LLM_TIMEOUT_S",
    "MODEL_EMBED",
)
REQUIRED: tuple[str, ...] = (
    "METERLESS_BASE_URL",
    "METERLESS_RUNTIME_TOKEN",
    "METERLESS_APP",
    "METERLESS_SCOPE",
    "MODEL_FAST",
    "MODEL_DEEP",
)
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
ROUTING_PREFIX = "meterless/"
SYSTEM_PROMPT = "TASK: healthcheck\nReply with one JSON object and nothing else."
EMBED_PROBE = "Valencia flash flood, Poyo ravine, 29 October 2024"


# --- config -----------------------------------------------------------------


def parse_env_file(text: str) -> dict[str, str]:
    """KEY=VALUE lines. Skips blanks and # comments; strips one pair of quotes."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key:
            out[key] = value
    return out


def load_values(env_path: Path, environ: Mapping[str, str]) -> dict[str, str]:
    # utf-8-sig: Notepad can save .env with a byte-order mark.
    values = parse_env_file(env_path.read_text(encoding="utf-8-sig")) if env_path.is_file() else {}
    for key in KEYS:
        if environ.get(key):
            values[key] = environ[key]
    return values


@dataclass
class Config:
    base_url: str
    token: str
    app: str
    scope: str
    model_fast: str
    model_deep: str
    timeout_s: float
    model_embed: str = ""

    def public_url(self) -> str:
        """Base URL without any user:password part."""
        parts = urllib.parse.urlsplit(self.base_url)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        return urllib.parse.urlunsplit((parts.scheme, host, parts.path, "", ""))


def build_config(
    values: Mapping[str, str], *, timeout: float | None = None
) -> tuple[Config | None, list[str]]:
    problems: list[str] = []
    get = {key: (values.get(key) or "").strip() for key in KEYS}
    for key in REQUIRED:
        if not get[key]:
            problems.append(f"{key} is empty.")
    if not get["METERLESS_RUNTIME_TOKEN"]:
        problems.append(
            "Paste the runtime token Nightshift issued for the floodsense-eu app "
            "into METERLESS_RUNTIME_TOKEN in the root .env."
        )
    base = get["METERLESS_BASE_URL"].rstrip("/")
    if "host.docker.internal" in base:
        problems.append(
            "METERLESS_BASE_URL uses host.docker.internal, the container URL. "
            "Host scripts need http://127.0.0.1:8088/v1."
        )
    elif base and not base.startswith(("http://", "https://")):
        problems.append("METERLESS_BASE_URL must start with http:// or https://.")
    timeout_s = timeout
    if timeout_s is None:
        try:
            timeout_s = float(get["LLM_TIMEOUT_S"] or 180)
        except ValueError:
            problems.append("LLM_TIMEOUT_S must be a number of seconds.")
            timeout_s = 180.0
    if problems:
        return None, problems
    return (
        Config(
            base_url=base,
            token=get["METERLESS_RUNTIME_TOKEN"],
            app=get["METERLESS_APP"],
            scope=get["METERLESS_SCOPE"],
            model_fast=get["MODEL_FAST"],
            model_deep=get["MODEL_DEEP"],
            timeout_s=timeout_s,
            model_embed=get["MODEL_EMBED"],
        ),
        [],
    )


# --- http -------------------------------------------------------------------


@dataclass
class Reply:
    status: int  # 0 when no HTTP response arrived
    body: str
    seconds: float
    error: str = ""

    def json(self) -> object:
        try:
            return json.loads(self.body)
        except ValueError:
            return None


class Client:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        host = urllib.parse.urlsplit(cfg.base_url).hostname or ""
        # A system or corporate proxy must not swallow a loopback runtime.
        handlers = [urllib.request.ProxyHandler({})] if host in LOOPBACK else []
        self._opener = urllib.request.build_opener(*handlers)

    def headers(self) -> dict[str, str]:
        # Same three headers as NightshiftClient._headers in the agents package.
        return {
            "Authorization": f"Bearer {self.cfg.token}",
            "meterless-app": self.cfg.app,
            "meterless-scope": self.cfg.scope,
            "Accept": "application/json",
        }

    def call(self, method: str, path: str, body: dict | None = None, *, timeout: float) -> Reply:
        headers = self.headers()
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.cfg.base_url + path, data=data, headers=headers, method=method
        )
        t0 = time.monotonic()
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return Reply(resp.status, text, time.monotonic() - t0)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return Reply(exc.code, text, time.monotonic() - t0)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", exc)
            return Reply(0, "", time.monotonic() - t0, error=str(reason) or type(exc).__name__)


# --- checks -----------------------------------------------------------------


@dataclass
class Check:
    name: str
    status: str  # PASS, FAIL, WARN or SKIP
    detail: str
    required: bool = True
    answered_by: str = ""


def snippet(text: str, limit: int = 140) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def explain(reply: Reply, cfg: Config) -> str:
    if reply.status == 0:
        return f"no response from {cfg.public_url()} ({reply.error}). Is Nightshift running?"
    body = snippet(reply.body)
    if reply.status in (401, 403):
        return (
            f"HTTP {reply.status}: token rejected or app not allowed. Check "
            f"METERLESS_RUNTIME_TOKEN and METERLESS_APP. Server said: {body}"
        )
    if reply.status == 404:
        return f"HTTP 404: check that METERLESS_BASE_URL ends in /v1. Server said: {body}"
    return f"HTTP {reply.status}: {body}"


def parse_json_reply(text: str) -> object:
    """Same tolerance as agents parse_json: ``` fences and prose around one object."""
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        return json.loads(t)
    except ValueError:
        pass
    start, depth = t.find("{"), 0
    for i in range(start, len(t)) if start >= 0 else []:
        depth += t[i] == "{"
        depth -= t[i] == "}"
        if depth == 0:
            try:
                return json.loads(t[start : i + 1])
            except ValueError:
                return None
    return None


def check_models(client: Client) -> tuple[Check, list[str], Reply]:
    cfg = client.cfg
    reply = client.call("GET", "/models", timeout=30)
    if reply.status != 200:
        return Check("GET /models", "FAIL", explain(reply, cfg)), [], reply
    data = reply.json()
    rows = data.get("data", []) if isinstance(data, dict) else []
    ids = [str(row.get("id", "")) for row in rows if isinstance(row, dict)]
    missing = [m for m in (cfg.model_fast, cfg.model_deep) if m not in ids]
    if missing:
        listed = ", ".join(f"`{m}`" for m in ids[:8]) or "none"
        return (
            Check(
                "GET /models",
                "FAIL",
                f"{len(ids)} listed; missing {', '.join(f'`{m}`' for m in missing)}. "
                f"Listed: {listed}",
            ),
            ids,
            reply,
        )
    return (
        Check("GET /models", "PASS", f"{len(ids)} listed; both pinned models present"),
        ids,
        reply,
    )


def lane_body(model: str, lane: str) -> dict:
    return {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Return exactly {{"ok": true, "lane": "{lane}"}}'},
        ],
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {"type": "json_object"},
        "max_tokens": 256,
    }


def check_lane(client: Client, lane: str, model: str) -> Check:
    cfg = client.cfg
    name = f"{lane} lane"
    body = lane_body(model, lane)
    json_mode = "on"
    reply = client.call("POST", "/chat/completions", body, timeout=cfg.timeout_s)
    if reply.status == 400 and "response_format" in reply.body:
        # The agents client drops JSON mode on exactly this error, so do the same.
        body.pop("response_format")
        json_mode = "off (runtime rejected response_format; agents fall back the same way)"
        reply = client.call("POST", "/chat/completions", body, timeout=cfg.timeout_s)
    if reply.status != 200:
        return Check(name, "FAIL", f"`{model}`: {explain(reply, cfg)}")
    data = reply.json()
    try:
        message = data["choices"][0]["message"]  # type: ignore[index]
        finish = data["choices"][0].get("finish_reason") or "?"  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        return Check(name, "FAIL", f"`{model}`: unexpected reply shape: {snippet(reply.body)}")
    content = (message.get("content") if isinstance(message, dict) else None) or ""
    returned = str(data.get("model") or model)  # type: ignore[union-attr]
    usage = data.get("usage") or {}  # type: ignore[union-attr]
    tokens = f"{usage.get('prompt_tokens', '?')} in / {usage.get('completion_tokens', '?')} out"
    facts = (
        f"`{returned}`, {reply.seconds:.1f} s, {tokens} tokens, finish {finish}, "
        f"JSON mode {json_mode}"
    )
    if not content.strip():
        hint = ""
        if isinstance(message, dict) and message.get("reasoning_content"):
            hint = " Only reasoning_content came back, so enable_thinking=false was ignored."
        return Check(name, "FAIL", f"{facts}. Empty content.{hint}")
    parsed = parse_json_reply(content)
    if not isinstance(parsed, dict):
        return Check(name, "FAIL", f"{facts}. Reply is not JSON: {snippet(content, 80)}")
    if "<think>" in content:
        facts += "; reply carried a <think> block"
    if parsed.get("ok") is not True:
        return Check(name, "WARN", f"{facts}. JSON parsed, ok is not true: {snippet(content, 80)}")
    if returned != model and not model.startswith(ROUTING_PREFIX):
        # A concrete model id answered by another model: routing overrode the pin.
        return Check(
            name,
            "WARN",
            f"{facts}. Pin not honoured: asked for `{model}`, answered by `{returned}`.",
            answered_by=returned,
        )
    if returned != model:
        # Routing modes are expected to resolve to a real model; record which one.
        facts += f"; routed by `{model}`"
    return Check(name, "PASS", facts, answered_by=returned)


def check_embeddings(client: Client, ids: list[str], *, enabled: bool, reachable: bool) -> Check:
    cfg = client.cfg
    name = "embeddings (optional)"
    if not enabled:
        return Check(name, "SKIP", "skipped (--no-embeddings)", required=False)
    if not reachable:
        return Check(name, "SKIP", "not run: /models failed", required=False)
    model = cfg.model_embed or next((m for m in ids if "embed" in m.lower()), "")
    if not model:
        return Check(
            name,
            "SKIP",
            "no embedding model listed by /models. The semantic cache needs one; "
            "set MODEL_EMBED to probe a specific id.",
            required=False,
        )
    reply = client.call("POST", "/embeddings", {"model": model, "input": [EMBED_PROBE]}, timeout=60)
    if reply.status in (404, 405):
        # /models answered on the same base URL, so the path is right; the route is missing.
        return Check(
            name,
            "WARN",
            f"`{model}` is listed, but POST /embeddings returned HTTP {reply.status}: this "
            "runtime does not serve embeddings. The semantic cache needs another source.",
            required=False,
        )
    if reply.status != 200:
        return Check(name, "WARN", f"`{model}`: {explain(reply, cfg)}", required=False)
    data = reply.json()
    try:
        vector = data["data"][0]["embedding"]  # type: ignore[index]
        dims = len(vector)
    except (KeyError, IndexError, TypeError):
        shape = snippet(reply.body)
        return Check(name, "WARN", f"`{model}`: unexpected reply shape: {shape}", required=False)
    return Check(name, "PASS", f"`{model}`, {dims} dims, {reply.seconds:.1f} s", required=False)


def run_checks(client: Client, *, embeddings: bool = True) -> list[Check]:
    cfg = client.cfg
    models, ids, reply = check_models(client)
    checks = [models]
    blocked = reply.status in (0, 401, 403)
    for lane, model in (("fast", cfg.model_fast), ("deep", cfg.model_deep)):
        if blocked:
            checks.append(Check(f"{lane} lane", "SKIP", "not run: /models got no usable answer"))
        else:
            checks.append(check_lane(client, lane, model))
    fast, deep = checks[1], checks[2]
    if (
        fast.status == "PASS"
        and deep.status == "PASS"
        and fast.answered_by
        and fast.answered_by == deep.answered_by
        and cfg.model_fast != cfg.model_deep
    ):
        # Both tiers collapsed onto one model, as a single race lane does.
        fast.status = "WARN"
        fast.detail += (
            f". Fast and deep were both answered by `{fast.answered_by}`: tiers not separate."
        )
    checks.append(check_embeddings(client, ids, enabled=embeddings, reachable=not blocked))
    return checks


# --- report -----------------------------------------------------------------


def verdict(checks: list[Check]) -> tuple[bool, int, int]:
    """(no required check failed, required checks passed or warned, required total)."""
    required = [c for c in checks if c.required]
    ok = sum(c.status in ("PASS", "WARN") for c in required)
    return ok == len(required), ok, len(required)


def scrub(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    # ASCII only: PowerShell 5 consoles default to a legacy code page.
    return text.encode("ascii", "replace").decode("ascii")


def render(cfg: Config, checks: list[Check], *, now: datetime) -> str:
    ok, passed, total = verdict(checks)
    warned = sum(c.status == "WARN" for c in checks if c.required)
    if not ok:
        result = f"**Result: FAIL** ({passed}/{total} required checks passed)"
    elif warned:
        result = (
            f"**Result: PASS with {warned} warning{'s' if warned > 1 else ''}** "
            f"({passed}/{total} required checks answered; see WARN rows)"
        )
    else:
        result = f"**Result: PASS** ({passed}/{total} required checks passed)"
    lines = [
        "## Nightshift live check",
        "",
        f"- When: {now.strftime('%Y-%m-%d %H:%M')} UTC{now.strftime('%z')}",
        f"- Runtime: {cfg.public_url()} (app `{cfg.app}`, scope `{cfg.scope}`)",
        f"- Lanes: fast `{cfg.model_fast}`, deep `{cfg.model_deep}`",
        "- Token: read from .env, not shown",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for c in checks:
        lines.append(f"| {c.name} | {c.status} | {c.detail.replace('|', '/')} |")
    lines += ["", result]
    return "\n".join(lines)


# --- cli --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nightshift_check.py",
        description="Check the local Nightshift runtime on both FloodSense lanes.",
    )
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV, help="Default: the root .env")
    parser.add_argument("--out", type=Path, help="Also write the markdown summary to this file.")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip the embeddings probe.")
    parser.add_argument("--timeout", type=float, help="Seconds per chat call (LLM_TIMEOUT_S)")
    return parser


def main(argv: list[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if environ is None else environ
    env_path: Path = args.env
    if not env_path.is_file() and not any(env.get(k) for k in REQUIRED):
        print(f"No env file at {env_path}. Nothing was sent.", file=sys.stderr)
        print(
            "Create it with: py tasks.py init-env, then fill METERLESS_RUNTIME_TOKEN.",
            file=sys.stderr,
        )
        return 2
    cfg, problems = build_config(load_values(env_path, env), timeout=args.timeout)
    if cfg is None:
        print(f"Config problems in {env_path.name}. Nothing was sent.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2
    checks = run_checks(Client(cfg), embeddings=not args.no_embeddings)
    report = scrub(render(cfg, checks, now=datetime.now().astimezone()), [cfg.token])
    print(report)
    if args.out:
        args.out.write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")
    return 0 if verdict(checks)[0] else 1


if __name__ == "__main__":
    raise SystemExit(main())
