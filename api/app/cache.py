"""Semantic cache and labelled replay, in front of the proxy.

GAMEPLAN "Caching and the honest demo". Both are off unless their flag is on.

Cache (FF_SEMANTIC_CACHE). A run is cached when it finished well: the analyst
approved or edited it and the Judge passed it. The key is the question
(case, spacing and punctuation folded) plus the event, the customer, the
replay clock, the language and the agents' flags, lanes and schema, so a
change of flags is a miss. A repeat of that question is answered with the
original run, which the agents label "Cached answer from HH:MM · not live ·
original run R". Live data expires sooner than a historical replay. A
follow-up in a thread is never cached or served from the cache, because it
depends on its conversation. "Similar" means the same after folding for now;
embedding similarity needs the embed lane.

Replay (FF_CACHED_REPLAY). When a live run fails (the agents answer 5xx, are
unreachable, or return a failed run), the API serves the newest recorded run
for the same event and customer that a person approved or edited, labelled
"Replay of a recorded run from HH:MM · not live · original run R", with the
reason. Follow-ups in a thread are not replayed for a new question. The
agents' checkpointer holds the recordings; the API also keeps the last few,
so a replay still works when the agents themselves are down.

The cache lives in this process. REDIS_URL is not read yet; a restart empties
the cache but not the recordings in the agents' checkpointer.
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

# Mirrors RunRequest's defaults in agents/floodsense_agents/models.py, so a
# request that leaves them out keys the same as one that spells them out.
DEFAULT_EVENT = "EMSR773"
DEFAULT_CUSTOMER = "demo-insurer"
DEFAULT_LANG = "en"
REMEMBERED = ("approved", "edited")
FLAGS_MEMO_S = 30.0


def _flag(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v in (None, "") else v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class CacheSettings:
    semantic_cache: bool = field(default_factory=lambda: _flag("FF_SEMANTIC_CACHE", False))
    cached_replay: bool = field(default_factory=lambda: _flag("FF_CACHED_REPLAY", False))
    ttl_live_s: float = field(
        default_factory=lambda: float(os.environ.get("CACHE_TTL_LIVE_S") or 900)
    )
    ttl_replay_s: float = field(
        default_factory=lambda: float(os.environ.get("CACHE_TTL_REPLAY_S") or 86400)
    )
    max_entries: int = field(
        default_factory=lambda: int(os.environ.get("CACHE_MAX_ENTRIES") or 256)
    )
    max_recordings: int = field(
        default_factory=lambda: int(os.environ.get("REPLAY_MAX_RECORDINGS") or 8)
    )


def fold(question: str) -> str:
    """The question as the cache compares it: casefolded, punctuation and spacing folded."""
    return " ".join(re.sub(r"[^\w\s]", " ", (question or "").casefold()).split())


def fingerprint(config: dict[str, Any]) -> str:
    """The agents' flags, lanes and schema, from their GET /config."""
    flags = config.get("flags") or {}
    lanes = config.get("lanes") or {}
    parts = [f"{k}={flags[k]}" for k in sorted(flags)]
    parts += [f"lane.{k}={lanes[k]}" for k in sorted(lanes)]
    parts.append(f"schema={config.get('schema')}")
    return ";".join(parts)


def key_of(request: dict[str, Any], flags: str) -> tuple:
    return (
        fold(str(request.get("question") or "")),
        request.get("event_id") or DEFAULT_EVENT,
        request.get("customer_id") or DEFAULT_CUSTOMER,
        request.get("replay_ts") or None,
        request.get("lang") or DEFAULT_LANG,
        flags,
    )


def approved_by_a_person(run: dict[str, Any]) -> bool:
    """Approved or edited by a reviewer. Enough for a recording to replay."""
    approval = (run.get("approval") or {}).get("status")
    return run.get("status") == "approved" and approval in REMEMBERED


def finished_well(run: dict[str, Any]) -> bool:
    """Approved or edited by a person, and passed by the Judge. Nothing else is cached."""
    return approved_by_a_person(run) and (run.get("judge_summary") or {}).get("passes") is True


def is_follow_up(run: dict[str, Any]) -> bool:
    request = run.get("request") or {}
    return bool(request.get("thread_id")) or (run.get("thread_id") or run.get("run_id")) != run.get(
        "run_id"
    )


@dataclass
class Entry:
    run_id: str
    stored_at: float  # time.time() when cached
    ttl_s: float


class AnswerCache:
    """Process-local cache of finished runs, plus the last few recordings for replay."""

    def __init__(self, settings: CacheSettings | None = None) -> None:
        self.settings = settings or CacheSettings()
        self._lock = threading.Lock()
        self._entries: OrderedDict[tuple, Entry] = OrderedDict()
        self._recordings: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._flags: tuple[float, str] | None = None

    # ---------------------------------------------------------------- flags

    def flags(self, fetch) -> str | None:
        """The agents' flag fingerprint, memoised briefly. None when /config fails."""
        now = time.monotonic()
        if self._flags and now - self._flags[0] < FLAGS_MEMO_S:
            return self._flags[1]
        config = fetch()
        if config is None:
            return None
        fp = fingerprint(config)
        self._flags = (now, fp)
        return fp

    def forget_flags(self) -> None:
        self._flags = None

    # ---------------------------------------------------------------- cache

    def ttl_for(self, request: dict[str, Any], flags: str) -> float:
        live_data = "FF_LIVE_DATA=True" in flags.split(";") and not request.get("replay_ts")
        return self.settings.ttl_live_s if live_data else self.settings.ttl_replay_s

    def remember(self, run: dict[str, Any], flags: str) -> bool:
        """Cache a finished run. False when it does not qualify."""
        if not finished_well(run) or is_follow_up(run):
            return False
        request = run.get("request") or {}
        key = key_of(request, flags)
        entry = Entry(run["run_id"], time.time(), self.ttl_for(request, flags))
        with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self.settings.max_entries:
                self._entries.popitem(last=False)
        return True

    def lookup(self, request: dict[str, Any], flags: str) -> Entry | None:
        if request.get("thread_id"):
            return None
        key = key_of(request, flags)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if time.time() - entry.stored_at > entry.ttl_s:
                del self._entries[key]
                return None
            return entry

    def drop(self, run_id: str) -> None:
        with self._lock:
            for key in [k for k, e in self._entries.items() if e.run_id == run_id]:
                del self._entries[key]

    # ------------------------------------------------------------ recordings

    def record(self, replay_body: dict[str, Any]) -> None:
        """Keep a replay-labelled run, for when the agents cannot be reached."""
        slot = (replay_body.get("event_id") or "", replay_body.get("customer_id") or "")
        with self._lock:
            self._recordings[slot] = replay_body
            self._recordings.move_to_end(slot)
            while len(self._recordings) > self.settings.max_recordings:
                self._recordings.popitem(last=False)

    def recording(self, event_id: str, customer_id: str) -> dict[str, Any] | None:
        with self._lock:
            body = self._recordings.get((event_id, customer_id))
            return dict(body) if body else None

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "FF_SEMANTIC_CACHE": self.settings.semantic_cache,
                "FF_CACHED_REPLAY": self.settings.cached_replay,
                "entries": len(self._entries),
                "recordings": len(self._recordings),
                "ttl_live_s": self.settings.ttl_live_s,
                "ttl_replay_s": self.settings.ttl_replay_s,
            }
