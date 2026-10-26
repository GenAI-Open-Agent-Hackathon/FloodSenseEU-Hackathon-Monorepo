"""Live mode: which question reads hazard_now instead of the event window.

An event run replays a frozen Copernicus window (EMSR773 is 28-30 Oct 2024).
A question about now, tonight or the next 48 hours asked of that window gets a
2024 answer, which is wrong in a way the citations cannot show. Live mode reads
{schema}.hazard_now instead: the past few days (Open-Meteo / GloFAS modelled)
and a ~48 h forecast, each row labelled by `horizon`.

resolve_mode() decides, deterministically:
  replay_ts set           event (a replay clock is a point in the event window)
  explicit mode           that mode
  question about now      live (EN, ES, DE time words below)
  anything else           event

api/app/cache.py keeps a copy of LIVE_PATTERNS so a cache key agrees with the
mode the agents will pick. Change both together.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from floodsense_agents.events import AHR_POINT_IDS, VALENCIA_POINT_IDS
from floodsense_agents.settings import settings

LIVE_DISABLED = (
    "live data disabled (FF_LIVE_DATA off): floodsense_seed.hazard_now holds the frozen "
    "replay window, not a past and a forecast"
)

LIVE = "live"
EVENT = "event"
FORECAST_HOURS = 48
# A forecast reaching less than this far past now means the sync is old.
STALE_FORECAST_H = 24
# The seed twin of hazard_now (migration 040) labels every row 'replay': it is
# the frozen 2024 window, not a present. Only past and forecast rows are live.
LIVE_ROWS = "horizon IN ('past', 'forecast')"

LIVE_PATTERNS: tuple[str, ...] = (
    r"now",
    r"right now",
    r"currently",
    r"today",
    r"tonight",
    r"tomorrow",
    r"this week",
    r"next \d+ ?(?:h|hours?|days?)",
    r"next (?:few )?(?:hours?|days?)",
    r"coming (?:hours?|days?)",
    # Spanish
    r"ahora",
    r"hoy",
    r"ma(?:ñ|n)ana",
    r"pr(?:ó|o)xim[ao]s \d+ ?(?:h|horas?)",
    # German. "Guten Morgen" is a greeting, not tomorrow.
    r"jetzt",
    r"heute",
    r"(?<!guten )morgen",
    r"n(?:ä|a)chsten \d+ ?(?:h|stunden)",
)
# A question that names the past is an event question, whatever else it says.
EVENT_PATTERNS: tuple[str, ...] = (
    r"(?:19\d{2}|20(?:[01]\d|2[0-4]))",  # a year up to 2024
    r"\d{4}-\d{2}-\d{2}",  # an explicit date
    r"\d{1,2}\.? (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|abr|ago|dic|"
    r"okt|dez|mai|juli?|juni?|m(?:ä|a)r)\w*",
    r"emsr\d*",
    r"on that day",
)
_EVENT_RE = re.compile(
    "|".join(rf"\b(?:{p})\b" for p in EVENT_PATTERNS), re.IGNORECASE | re.UNICODE
)
_LIVE_RE = re.compile(
    "|".join(rf"\b(?:{p})\b" for p in LIVE_PATTERNS), re.IGNORECASE | re.UNICODE
)


def classify(question: str) -> tuple[str, str]:
    """(mode, reason) from the question alone."""
    past = _EVENT_RE.search(question or "")
    if past:
        return EVENT, f"question names a past moment ('{past.group(0)}')"
    m = _LIVE_RE.search(question or "")
    if m:
        return LIVE, f"question asks about the present ('{m.group(0)}')"
    return EVENT, "question names no present-time window"


def resolve_mode(request: dict) -> dict:
    """The effective mode of a run, why, and whether the caller chose it."""
    explicit = request.get("mode")
    if request.get("replay_ts"):
        return {
            "mode": EVENT,
            "explicit": explicit,
            "reason": "replay_ts is set, so the run replays the event window",
        }
    if explicit == LIVE and not settings.live_data:
        return {"mode": LIVE, "explicit": LIVE, "reason": f"mode=live requested, but {LIVE_DISABLED}"}
    if explicit in (LIVE, EVENT):
        return {"mode": explicit, "explicit": explicit, "reason": f"mode={explicit} requested"}
    mode, reason = classify(str(request.get("question") or ""))
    if mode == LIVE and not settings.live_data:
        return {"mode": EVENT, "explicit": None, "reason": f"{reason}, but {LIVE_DISABLED}"}
    return {"mode": mode, "explicit": None, "reason": reason}


def is_live(state: dict) -> bool:
    return (state.get("mode") or {}).get("mode") == LIVE


def live_points(event: dict) -> tuple[str, ...]:
    """Every warehouse point of the event's region. hazard_now holds all of them."""
    if str(event.get("event_id")) == "EMSR517":
        return AHR_POINT_IDS
    return VALENCIA_POINT_IDS


def points_sql(event: dict) -> str:
    return ", ".join(f"'{p}'" for p in live_points(event))


def horizon_word(horizon: str | None) -> str:
    if horizon == "forecast":
        return "forecast"
    return "past (observed-modelled)"


def hours_between(ts: str, now: str) -> int | None:
    try:
        a = datetime.strptime(str(ts)[:19].replace(" ", "T"), "%Y-%m-%dT%H:%M:%S")
        b = datetime.strptime(str(now)[:19].replace(" ", "T"), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    return round((a - b).total_seconds() / 3600)


def relative(ts: str, now: str) -> str:
    """'in 17 h' / '5 h ago' between two UTC stamps. Blank when unreadable."""
    try:
        a = datetime.strptime(str(ts)[:19].replace(" ", "T"), "%Y-%m-%dT%H:%M:%S")
        b = datetime.strptime(str(now)[:19].replace(" ", "T"), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""
    delta = a.replace(tzinfo=timezone.utc) - b.replace(tzinfo=timezone.utc)
    hours = round(delta.total_seconds() / 3600)
    if hours > 0:
        return f"in {hours} h"
    if hours < 0:
        return f"{-hours} h ago"
    return "this hour"
