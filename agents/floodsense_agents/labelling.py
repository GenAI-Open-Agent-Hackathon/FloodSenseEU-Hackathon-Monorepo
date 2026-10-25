"""One place that decides how a non-live answer is described.

GAMEPLAN "Caching and the honest demo": every response carries served_from
of live, cache or replay, and cached_at when it is not live. Cached or
replayed output is never presented as live, in the UI, the video or the
deck.

The wording is built here rather than in a UI so every surface says the
same thing: this console, the team's console when it lands, and anything
that reads the API later. A UI only has to render label.text when
label.live is false.
"""

from __future__ import annotations

from typing import Any

LIVE = "live"
CACHE = "cache"
REPLAY = "replay"
KINDS = (LIVE, CACHE, REPLAY)


def computation_label(replay_ts: str | None, *, live: bool) -> tuple[str, str | None]:
    """How a run that was just computed should be labelled.

    ``live`` is true only for a fresh read of the live schema through live
    Zetaris, with no replay clock. Fake rows, the seed schema, and a replay
    clock are a replay: the answer was not read from the world just now.
    ``cached_at`` is the replay clock when there is one, otherwise the time
    the answer was produced. A later re-read of the same run is cache.
    """
    if live and not replay_ts:
        return LIVE, None
    # Imported here so labelling stays usable without pulling the SQL client
    # in at module import for the pure label() helpers.
    from floodsense_agents.models import normalize_utc
    from floodsense_agents.zetaris import now_utc

    if replay_ts:
        return REPLAY, normalize_utc(replay_ts)
    return REPLAY, now_utc()


def _hhmm(ts: str | None) -> str | None:
    """14:32 out of 2026-10-24T14:32:51Z. None when there is no usable stamp."""
    if not ts or len(ts) < 16 or ts[10] not in ("T", " "):
        return None
    return ts[11:16]


def label(
    served_from: str | None, cached_at: str | None = None, run_id: str | None = None
) -> dict[str, Any]:
    """How to describe this answer. Anything unrecognised is not called live."""
    kind = served_from if served_from in KINDS else None
    if kind == LIVE:
        return {"live": True, "kind": LIVE, "text": None, "at": None}

    at = _hhmm(cached_at)
    if kind == CACHE:
        head = f"Cached answer from {at}" if at else "Cached answer"
    elif kind == REPLAY:
        head = f"Replay of a recorded run from {at}" if at else "Replay of a recorded run"
    else:
        # Unknown provenance is the one case where saying nothing would be
        # worse than saying so.
        head = "Provenance not recorded"
    parts = [head, "not live"]
    if run_id:
        parts.append(f"original run {run_id}")
    return {"live": False, "kind": kind or "unknown", "text": " · ".join(parts), "at": at}


def labelled(body: dict[str, Any]) -> dict[str, Any]:
    """Add served_from, cached_at and the label to a response body."""
    body.setdefault("served_from", LIVE)
    body.setdefault("cached_at", None)
    body["label"] = label(body["served_from"], body["cached_at"], body.get("run_id"))
    return body
