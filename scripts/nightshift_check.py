"""Nightshift live check for FloodSense EU. Host side, stdlib only.

Proves that this machine's Meterless Nightshift runtime answers the same
request the agents client (agents/floodsense_agents/nightshift.py) sends,
on both lanes.

    python scripts/nightshift_check.py
    python scripts/nightshift_check.py --out nightshift-check.md
    python scripts/nightshift_check.py --probe

Reads the root .env (host URLs on 127.0.0.1, not agents/.env). A non-empty
environment variable overrides the file. MODEL_FAST and MODEL_DEEP are
Nightshift routing modes (meterless/fast, meterless/deep): Nightshift picks
the lane, and each reply names the model that answered. Each tier has a
wanted model, EXPECT_MODEL_FAST and EXPECT_MODEL_DEEP. Both default to
Nemotron 3.5 Super VL 120B A12B, which Nightshift picks for both tiers today
because it is the faster lane as well as the stronger one. Set
EXPECT_MODEL_FAST to the Lightning 30B id to hold fast to it, or set either
to "any" to accept whichever model answers. Checks, in order:

  1. GET  /models            MODEL_FAST and MODEL_DEEP are listed. A
                             missing model name fails; a missing meterless/
                             routing mode is a warning, because Nightshift
                             also takes composed ids (meterless/text.fast).
  2. POST /chat/completions  one tiny JSON reply per tier, with the agents
                             client's body: temperature 0.1, thinking off,
                             JSON mode, and the same 400 fallback. Only the
                             check caps the reply (CHECK_MAX_TOKENS); the
                             client sets no cap. A reply
                             from a model other than the tier's wanted one
                             is a warning. When the tiers want different
                             models, so is both answered by one model.
  3. POST /embeddings        optional probe for the semantic cache. No
                             embedding model is reported, not failed.

--probe sends every candidate id (the listed text routing modes, the
composed fast/deep variants and the wanted model names) --probe-rounds times
each, shows which model answered, and suggests MODEL_FAST and MODEL_DEEP
values that reached the wanted model every time. It skips local, fusion,
cluster, embedding and media modes, so it never starts a local model load.
The report always has a Rounds heading and a Skipped heading, including when
/models gives no list or a round is not sent. It also lists any routing
details Nightshift returns beyond the model name (meterless-* headers and
extra reply fields), such as which lanes raced.

Prints a markdown summary that is safe to paste into a PR. The runtime token
is never printed: it is scrubbed from every server reply as it arrives,
before any text is cut short for the report.
Exit 0 when no required check fails (warnings included), 1 when one fails,
2 on a config error. --probe exits 0 when both tiers have a suggestion.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
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
    "EXPECT_MODEL_FAST",
    "EXPECT_MODEL_DEEP",
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
# The model each tier should land on. Nightshift answers both tiers with
# Super VL 120B today: it replied in about 0.5 s against 2.6 s for Lightning
# 30B, and it is the stronger model. EXPECT_MODEL_FAST overrides the fast one.
WANT_DEEP = "nvidia/nemotron-3.5-super-vl-120b-a12b"
WANT_FAST = WANT_DEEP
# Reply fields every OpenAI-compatible server sends; anything else is a detail
# the runtime added (a receipt, the lanes that raced) and the probe lists it.
STANDARD_REPLY_KEYS = frozenset(
    {"id", "object", "created", "model", "choices", "usage", "system_fingerprint", "service_tier"}
)
ANY_MODEL = "any"
# Probe candidates beyond what /models lists. Composed ids are documented as
# meterless/<class>.<disposition>; Nightshift does not list every combination.
PROBE_SEEDS: tuple[str, ...] = (
    "meterless/fast",
    "meterless/deep",
    "meterless/auto",
    "meterless/cheap",
    "meterless/text",
    "meterless/text.fast",
    "meterless/text.deep",
    "meterless/vision",
    "meterless/vision.fast",
    "meterless/vision.deep",
    "meterless/judge",
    "meterless/verify",
)
# Never probe these: local can start a model download, fusion and cluster fan
# out to several routes, and embedding or media modes are not chat.
PROBE_SKIP = re.compile(
    r"^meterless/(local|fusion|cluster|embed|image|video|speech|audio|tts|stt|music|voice"
    r"|transcribe)\b|\.(local|fusion|cluster)$"
)
PROBE_MAX_IDS = 20
PROBE_MAX_ROUNDS = 10
# Timeouts in seconds. Chat calls use LLM_TIMEOUT_S (or --timeout); the probe
# caps each call at PROBE_TIMEOUT_CAP_S so a hung id cannot stall it for long.
MODELS_TIMEOUT_S = 30
EMBED_TIMEOUT_S = 60
PROBE_TIMEOUT_CAP_S = 90
# The check asks for a one-line JSON reply, so it caps the answer; the agents
# client sends the same body without a cap.
CHECK_MAX_TOKENS = 256


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
    want_fast: str = WANT_FAST  # "" accepts any model
    want_deep: str = WANT_DEEP

    def want(self, lane: str) -> str:
        return self.want_fast if lane == "fast" else self.want_deep

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
            "Host scripts need the 127.0.0.1 URL from the root .env.example."
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

    def want(key: str, default: str) -> str:
        value = get[key] or default
        return "" if value.lower() == ANY_MODEL else value

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
            want_fast=want("EXPECT_MODEL_FAST", WANT_FAST),
            want_deep=want("EXPECT_MODEL_DEEP", WANT_DEEP),
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
    headers: dict[str, str] = field(default_factory=dict)  # lower-case names

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
                return Reply(
                    resp.status,
                    self.scrub(text),
                    time.monotonic() - t0,
                    headers=self.header_map(resp.headers),
                )
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return Reply(
                exc.code,
                self.scrub(text),
                time.monotonic() - t0,
                headers=self.header_map(exc.headers),
            )
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = str(getattr(exc, "reason", exc)) or type(exc).__name__
            return Reply(0, "", time.monotonic() - t0, error=self.scrub(reason))

    def scrub(self, text: str) -> str:
        """Drop the token from server text before anything cuts it short."""
        return text.replace(self.cfg.token, "***") if self.cfg.token else text

    def header_map(self, headers: object) -> dict[str, str]:
        items = headers.items() if hasattr(headers, "items") else []
        return {str(k).lower(): self.scrub(str(v)) for k, v in items}


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


def error_fields(body: str) -> str:
    """A JSON error object in full (message, code, and Nightshift's own fields), or ""."""
    try:
        data = json.loads(body)
    except ValueError:
        return ""
    err = data.get("error") if isinstance(data, dict) else None
    if not isinstance(err, dict):
        return ""
    parts = []
    for key, value in err.items():
        if value in (None, "", [], {}):
            continue
        text = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
        parts.append(f"{key}={text}")
    return snippet("; ".join(parts), 600)


def explain(reply: Reply, cfg: Config) -> str:
    if reply.status == 0:
        return f"no response from {cfg.public_url()} ({reply.error}). Is Nightshift running?"
    body = error_fields(reply.body) or snippet(reply.body)
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
    reply = client.call("GET", "/models", timeout=MODELS_TIMEOUT_S)
    if reply.status != 200:
        return Check("GET /models", "FAIL", explain(reply, cfg)), [], reply
    data = reply.json()
    rows = data.get("data", []) if isinstance(data, dict) else []
    ids = [str(row.get("id", "")) for row in rows if isinstance(row, dict)]
    missing = [m for m in dict.fromkeys((cfg.model_fast, cfg.model_deep)) if m not in ids]
    if not missing:
        return (
            Check("GET /models", "PASS", f"{len(ids)} listed; MODEL_FAST and MODEL_DEEP present"),
            ids,
            reply,
        )
    modes = [m for m in ids if m.startswith(ROUTING_PREFIX)]
    listed = ", ".join(f"`{m}`" for m in (modes or ids)[:24]) or "none"
    names = ", ".join(f"`{m}`" for m in missing)
    if all(m.startswith(ROUTING_PREFIX) for m in missing):
        # Composed modes (meterless/<class>.<disposition>) are valid without a listing.
        status, why = "WARN", "not listed, but composed routing modes can still route"
    else:
        status, why = "FAIL", "missing"
    detail = f"{len(ids)} listed; {why}: {names}. Routing modes listed: {listed}"
    return Check("GET /models", status, detail), ids, reply


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
        "max_tokens": CHECK_MAX_TOKENS,
    }


def send_chat(client: Client, model: str, lane: str, *, timeout: float) -> tuple[Reply, str]:
    """One chat call with the agents client's body and its JSON-mode fallback."""
    body = lane_body(model, lane)
    reply = client.call("POST", "/chat/completions", body, timeout=timeout)
    if reply.status == 400 and "response_format" in reply.body:
        # The agents client drops JSON mode on exactly this error, so do the same.
        body.pop("response_format")
        reply = client.call("POST", "/chat/completions", body, timeout=timeout)
        return reply, "off (runtime rejected response_format; agents fall back the same way)"
    return reply, "on"


def answering_model(reply: Reply) -> str:
    """The model a 200 reply says answered, or "" when it does not say."""
    data = reply.json()
    return str(data.get("model") or "") if isinstance(data, dict) else ""


def check_lane(client: Client, lane: str, model: str) -> Check:
    cfg = client.cfg
    name = f"{lane} lane"
    want = cfg.want(lane)
    reply, json_mode = send_chat(client, model, lane, timeout=cfg.timeout_s)
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
    if want and returned != want:
        return Check(
            name,
            "WARN",
            f"{facts}. Wrong model for the {lane} tier: it should be `{want}`. "
            "Run with --probe to find an id that reaches it.",
            answered_by=returned,
        )
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
    body = {"model": model, "input": [EMBED_PROBE]}
    reply = client.call("POST", "/embeddings", body, timeout=EMBED_TIMEOUT_S)
    if reply.status in (404, 405):
        # /models answered on the same base URL, so the path is right; the route is missing.
        return Check(
            name,
            "WARN",
            f"`{model}` is listed, but POST /embeddings returned HTTP {reply.status}. "
            "Nightshift answers embeddings from a lane with the embed duty (for example "
            "Nemotron 3 Embed 1B); add one, then run this again.",
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
    blocked = reply.status in (0, 401, 403)

    def lane_check(lane: str, model: str) -> Check:
        if blocked:
            return Check(f"{lane} lane", "SKIP", "not run: /models got no usable answer")
        return check_lane(client, lane, model)

    fast = lane_check("fast", cfg.model_fast)
    deep = lane_check("deep", cfg.model_deep)
    if (
        fast.status in ("PASS", "WARN")
        and fast.answered_by
        and fast.answered_by == deep.answered_by
        and cfg.model_fast != cfg.model_deep
        and cfg.want_fast != cfg.want_deep
    ):
        # The tiers want different models but collapsed onto one, as a single race lane does.
        fast.status = "WARN"
        stop = "" if fast.detail.endswith(".") else "."
        fast.detail += (
            f"{stop} Fast and deep were both answered by `{fast.answered_by}`: tiers not separate."
        )
    embed = check_embeddings(client, ids, enabled=embeddings, reachable=not blocked)
    return [models, fast, deep, embed]


# --- probe ------------------------------------------------------------------


@dataclass
class Probe:
    model: str
    listed: bool
    answers: list[str] = field(default_factory=list)  # a model name, or "(HTTP 400)" and such
    seconds: list[float] = field(default_factory=list)
    details: dict[str, str] = field(default_factory=dict)  # routing details from the first reply

    def always(self, want: str) -> bool:
        """Every reply came from `want`, and at least half the rounds got a reply.

        An upstream 502 is the provider failing, not a routing decision, so it
        does not count against the route unless it is most of the rounds.
        """
        replies = [a for a in self.answers if not a.startswith("(")]
        enough = len(replies) * 2 >= len(self.answers)
        return bool(replies) and enough and all(a == want for a in replies)

    def summary(self, rounds: int) -> str:
        n = len(self.answers)
        parts = [
            f"{a} {c}/{n}" if a.startswith("(") else f"`{a}` {c}/{n}"
            for a, c in Counter(self.answers).most_common()
        ]
        text = ", ".join(parts)
        if not text:
            return "skipped"
        left = rounds - n
        if left > 0:
            text += f"; {left} round{'s' if left != 1 else ''} skipped"
        return text


def probe_plan(cfg: Config, ids: list[str]) -> tuple[list[str], list[str]]:
    """Ids to send, and ids left out so a local model load never starts."""
    listed_modes = [m for m in ids if m.startswith(ROUTING_PREFIX)]
    pool = [*PROBE_SEEDS, cfg.model_fast, cfg.model_deep, cfg.want_fast, cfg.want_deep]
    pool += listed_modes
    ordered = [m for m in dict.fromkeys(pool) if m]
    skipped = [m for m in ordered if PROBE_SKIP.search(m)]
    keep = [m for m in ordered if not PROBE_SKIP.search(m)]
    return keep[:PROBE_MAX_IDS], skipped


def probe_candidates(cfg: Config, ids: list[str]) -> list[str]:
    """Seeds, then the configured ids, the wanted model names and other listed modes."""
    return probe_plan(cfg, ids)[0]


def run_probe(client: Client, *, rounds: int) -> tuple[Check, list[Probe], list[str], bool]:
    """Models check, per-id probes, skipped ids, and whether id selection ran.

    The last flag is false when /models gave no list. The skipped list is then
    empty because the probe stopped before choosing ids.
    """
    cfg = client.cfg
    models, ids, reply = check_models(client)
    if reply.status != 200:
        return models, [], [], False
    keep, skipped = probe_plan(cfg, ids)
    timeout = min(cfg.timeout_s, PROBE_TIMEOUT_CAP_S)
    probes: list[Probe] = []
    for model in keep:
        probe = Probe(model, model in ids)
        for _ in range(rounds):
            got, _json_mode = send_chat(client, model, "probe", timeout=timeout)
            if got.status == 200:
                probe.answers.append(answering_model(got) or "(model not named)")
                probe.seconds.append(got.seconds)
                if not probe.details:
                    probe.details = routing_details(got)
                continue
            probe.answers.append("(no reply)" if got.status == 0 else f"(HTTP {got.status})")
            if got.status < 500:
                # A refusal (4xx) or no runtime will not change on the next round.
                # A 5xx is usually the upstream provider; try again.
                break
        probes.append(probe)
    return models, probes, skipped, True


def routing_details(reply: Reply) -> dict[str, str]:
    """What the runtime says about the route beyond the model name."""
    found = {k: v for k, v in reply.headers.items() if "meterless" in k or "nightshift" in k}
    data = reply.json()
    if isinstance(data, dict):
        for key, value in data.items():
            if key not in STANDARD_REPLY_KEYS:
                found[key] = json.dumps(value, separators=(",", ":"))
    return {k: snippet(v, 160) for k, v in sorted(found.items())}


def suggest(probes: list[Probe], want: str, lane: str) -> str:
    """First id that reached `want` every round.

    Routing modes before model names, then ids that name the tier (so deep
    gets meterless/deep rather than meterless/fast when both land there), then
    listed ids, then candidate order.
    """
    if not want:
        return ""
    good = [p for p in probes if p.always(want)]
    good.sort(
        key=lambda p: (
            not p.model.startswith(ROUTING_PREFIX),
            lane not in p.model.removeprefix(ROUTING_PREFIX),
            not p.listed,
        )
    )
    return good[0].model if good else ""


def render_probe(
    cfg: Config,
    models: Check,
    probes: list[Probe],
    *,
    rounds: int,
    now: datetime,
    env_name: str,
    skipped: list[str],
    chose_ids: bool,
) -> tuple[str, bool]:
    lines = [
        "## Nightshift routing probe",
        "",
        f"- When: {when_label(now)}",
        f"- Runtime: {cfg.public_url()} (app `{cfg.app}`, scope `{cfg.scope}`)",
        f"- Wanted: fast `{cfg.want_fast or ANY_MODEL}`, deep `{cfg.want_deep or ANY_MODEL}`",
        f"- Each id sent up to {rounds} times with the agents client's request body",
        f"- Token: read from {env_name}, not shown",
        "",
        "### Rounds",
        "",
    ]
    if not probes:
        if chose_ids:
            reason = "Skipped. Every candidate id was left out, so no rounds were sent."
        else:
            reason = "Skipped. /models gave no list, so no rounds were sent."
        lines += [
            reason,
            "",
            "| Check | Result | Detail |",
            "|---|---|---|",
            f"| {models.name} | {models.status} | {models.detail.replace('|', '/')} |",
            "",
        ]
    else:
        lines += ["| Model id sent | Listed | Answered by | Median time |", "|---|---|---|---|"]
        for p in probes:
            median = f"{statistics.median(p.seconds):.1f} s" if p.seconds else "-"
            answered = p.summary(rounds).replace("|", "/")
            lines.append(
                f"| `{p.model}` | {'yes' if p.listed else 'no'} | {answered} | {median} |"
            )
        lines.append("")
    lines += ["### Skipped", ""]
    if not chose_ids:
        lines += ["Not evaluated. The probe stopped before choosing ids.", ""]
    elif skipped:
        listed = ", ".join(f"`{m}`" for m in skipped)
        lines += [
            "Not sent, so a local model is never loaded "
            f"(local, fusion, cluster, embedding, or media): {listed}.",
            "",
        ]
    else:
        lines += ["None. No candidate was a local, fusion, cluster, embedding, or media mode.", ""]
    if not probes:
        if chose_ids:
            lines.append("**Result: probe not run** (every candidate id was skipped)")
        else:
            lines.append("**Result: probe not run** (/models gave no list)")
        return "\n".join(lines), False
    picks, gaps = [], []
    for lane, want in (("fast", cfg.want_fast), ("deep", cfg.want_deep)):
        if not want:
            continue
        pick = suggest(probes, want, lane)
        if pick:
            picks.append(f"MODEL_{lane.upper()}={pick}")
        else:
            gaps.append(
                f"**{lane.capitalize()}: no id reached `{want}` every time.** Nightshift's "
                "lane setup decides which model answers; change the lanes and probe again."
            )
    lines.append("")
    if picks:
        lines += ["**Suggested settings** (every round reached the wanted model):", "", "```"]
        lines += [*picks, "```", ""]
    lines += [*gaps, *([""] if gaps else [])]
    detailed = [p for p in probes if p.details]
    if detailed:
        lines += ["**Runtime details** (first reply per id, beyond the model name):", ""]
        for p in detailed[:20]:
            facts = "; ".join(f"`{k}` = {v.replace('|', '/')}" for k, v in p.details.items())
            lines.append(f"- `{p.model}`: {facts}")
        lines.append("")
    else:
        lines += ["Nightshift returned no routing details beyond the model name.", ""]
    if gaps:
        lines.append(
            f"**Result: {len(gaps)} tier{'s' if len(gaps) > 1 else ''} without a reliable id**"
        )
    else:
        lines.append("**Result: every tier has a reliable id**")
    return "\n".join(lines), not gaps


# --- report -----------------------------------------------------------------


def when_label(now: datetime) -> str:
    """Local time with its offset, e.g. 2026-10-25 02:16 UTC+0530."""
    return f"{now.strftime('%Y-%m-%d %H:%M')} UTC{now.strftime('%z')}"


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


def render(cfg: Config, checks: list[Check], *, now: datetime, env_name: str = ".env") -> str:
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
        f"- When: {when_label(now)}",
        f"- Runtime: {cfg.public_url()} (app `{cfg.app}`, scope `{cfg.scope}`)",
        f"- Lanes: fast `{cfg.model_fast}`, deep `{cfg.model_deep}`",
        f"- Wanted: fast `{cfg.want_fast or ANY_MODEL}`, deep `{cfg.want_deep or ANY_MODEL}`",
        f"- Token: read from {env_name}, not shown",
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
    parser.add_argument(
        "--probe",
        action="store_true",
        help=(
            "Find which model ids reach each tier's wanted model, and suggest settings. "
            f"Worst case: {PROBE_MAX_IDS} ids x --probe-rounds cloud calls, each capped at "
            f"{PROBE_TIMEOUT_CAP_S} s; a healthy runtime answers each in about a second."
        ),
    )
    parser.add_argument(
        "--probe-rounds",
        type=int,
        default=3,
        help=f"Times to send each id (default 3, at most {PROBE_MAX_ROUNDS}).",
    )
    return parser


def main(argv: list[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if environ is None else environ
    env_path: Path = args.env
    if not env_path.is_file() and not any(env.get(k) for k in REQUIRED):
        print(f"No env file at {env_path}. Nothing was sent.", file=sys.stderr)
        print(
            "Create it with: python tasks.py init-env, then fill METERLESS_RUNTIME_TOKEN.",
            file=sys.stderr,
        )
        return 2
    cfg, problems = build_config(load_values(env_path, env), timeout=args.timeout)
    if cfg is None:
        print(f"Config problems in {env_path.name}. Nothing was sent.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2
    now = datetime.now().astimezone()
    if args.probe:
        rounds = max(1, min(args.probe_rounds, PROBE_MAX_ROUNDS))
        if rounds != args.probe_rounds:
            print(
                f"note: --probe-rounds {args.probe_rounds} is outside 1 to {PROBE_MAX_ROUNDS}; "
                f"using {rounds}.",
                file=sys.stderr,
            )
        models, probes, skipped, chose_ids = run_probe(Client(cfg), rounds=rounds)
        text, ok = render_probe(
            cfg,
            models,
            probes,
            rounds=rounds,
            now=now,
            env_name=env_path.name,
            skipped=skipped,
            chose_ids=chose_ids,
        )
    else:
        checks = run_checks(Client(cfg), embeddings=not args.no_embeddings)
        text, ok = render(cfg, checks, now=now, env_name=env_path.name), verdict(checks)[0]
    report = scrub(text, [cfg.token])
    print(report)
    if args.out:
        args.out.write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
