"""The forecast lane: "Do the next 48 hours look safe at Köln?" for the 45 watched places.

    scope ─┬─ lane=forecast → forecast_data → history → forecast_answer → forecast_judge ─┬─ pass → END (answered)
           │                                                                              └─ flag / no data → escalate → watchers
           └─ declined → END (a decline is never overridden)

Places are watch.FORECAST_POINTS: 26 PEGELONLINE gauges (PEG01-PEG26), 11 GloFAS
eu_watch points (EU01-EU11) and 8 Valencia points (VAL01-VAL08), resolved from the
question (watch.watch_target, then the Valencia town names), else the user's selection.
At most MAX_PLACES are read.

forecast_data   one parallel batch of Zetaris reads per run, for every asked place:
                {schema}.weather_forecast  rain sums for the next 48 h / 72 h and the
                                           wettest hour (Open-Meteo, DWD ICON)
                {schema}.eu_watch          GloFAS forecast max vs the past-30-day median (eu)
                {schema}.hazard_now        forecast max discharge vs the anomaly line (valencia)
                {schema}.gauge_levels      current level, MHW and trend (gauge)
history         the past pattern for a place in Valencia (EMSR773) or the Rhine basin
                (EMSR517, the Ahr joins the Rhine): one replay-seed aggregate of
                floodsense_seed.hazard_timeline (48 h rain before the peak, peak
                discharge), the top RAG passage (retrieve_docs with "<place> flood ..."),
                and H-MEM recall for that place (seeded memories labelled). The three
                run in parallel; a slow or failed one becomes a trace note.
forecast_answer deterministic claims, one per evidence item, each citing only its own
                query, passage or memory. Then ONE fast-lane call writes a two-sentence
                "Outlook (model-written)"; it is kept only when it states no number and
                no place the data claims do not carry (outlook_ok), else dropped. Status
                Normal / Watch / Warning is a FloodSense screening cut, never official.
forecast_judge  judge.evaluate with no model (quick.quick_judge): a pass ends the run
                as answered; any flag escalates to the full lane.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

from floodsense_agents.engines import memory_origin, short
from floodsense_agents.events import EVENTS, POINT_NAMES
from floodsense_agents.governance import DEFINITIONS
from floodsense_agents.live import GAUGE_STALE_H, gauge_latest_sql, gauge_threshold, hours_between
from floodsense_agents.models import Citation, Claim, Evidence
from floodsense_agents.nightshift import parse_json, submit_with_deadline
from floodsense_agents.nodes import quick
from floodsense_agents.nodes.investigator import (
    _DOC_SQL,
    _cite_passage,
    _doc_text,
    _verified_raw,
    cite,
    numbers_in,
)
from floodsense_agents.settings import settings
from floodsense_agents.state import Deps, FloodState, add_evidence, trace
from floodsense_agents.watch import (
    FORECAST_BY_ID,
    FORECAST_BY_REF,
    ForecastPoint,
    place_words,
    sql_list,
    watch_target,
)
from floodsense_agents.zetaris import now_utc, run_sql_parallel

log = logging.getLogger("floodsense.forecast")

FORECAST = "forecast"
MAX_PLACES = 3
HORIZON_H = 48
# The Rhine basin: the Ahr joins the Rhine between Koblenz and Bonn, so a gauge on
# these waters is compared with the July 2021 Ahr flood.
RHINE_BASIN = ("RHEIN", "MOSEL", "SAAR", "MAIN", "NECKAR")
# The replay-seed pattern per event: the 48 h before the end of the peak day, inside
# the event window. Ahr: 13-14 Jul 2021 at Altenahr (AHR01). Valencia: 28-29 Oct 2024
# at the asked point (every VAL point has seed rows).
PATTERNS: dict[str, dict[str, str]] = {
    "EMSR517": {
        "point": "AHR01",
        "label": "July 2021 Ahr flood",
        "days": "13-14 Jul 2021",
        "rain_from": "2021-07-13T00:00:00Z",
        "rain_to": "2021-07-15T00:00:00Z",
    },
    "EMSR773": {
        "point": "",
        "label": "October 2024 Valencia DANA flood",
        "days": "28-29 Oct 2024",
        "rain_from": "2024-10-28T00:00:00Z",
        "rain_to": "2024-10-30T00:00:00Z",
    },
}
# Status cuts. FloodSense's own screening, declared here and in agents/README.md;
# none of them is an official warning threshold.
RAIN_WARN_MM = float(DEFINITIONS["anomaly_rain_total"].value)  # 50 mm in 48 h
RAIN_WATCH_MM = RAIN_WARN_MM / 2  # 25 mm in 48 h
HOUR_WARN_MM = float(DEFINITIONS["anomaly_rain"].value)  # 30 mm in one hour
HOUR_WATCH_MM = float(DEFINITIONS["extreme_rain"].value)  # 20 mm in one hour
DISCHARGE_LINE = float(DEFINITIONS["anomaly_discharge"].value)  # 100 m3/s (Valencia points)
NORMAL, WATCH, WARNING = "Normal", "Watch", "Warning"
_RANK = {NORMAL: 0, WATCH: 1, WARNING: 2}
# Who to follow, by country of the place.
OFFICIAL: dict[str, str] = {
    "DE": "DWD warnings and the Hochwassermeldedienst of your Land (NINA app)",
    "ES": "AEMET and Protección Civil (ES-Alert)",
    "FR": "Vigicrues and Météo-France",
    "IT": "the Protezione Civile and your regional ARPA",
    "PL": "IMGW-PIB",
    "AT": "GeoSphere Austria and the hydrographic service of your Land",
    "HU": "HungaroMet and the water directorate (OVF, vizugy.hu)",
    "BE": "the RMI/KMI and your regional hydrological service",
    "CZ": "the CHMI (ČHMÚ)",
}

OUTLOOK_SYSTEM = """TASK: forecast_outlook
Write a plain-language outlook for a member of the public: EXACTLY two short sentences.
Use only the STATUS and FACTS below. Do not add any number, date, place, river or source
that the FACTS do not state. Do not call it an official warning and do not give orders.
Answer with JSON only: {"outlook": "..."}"""

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="forecast")
_VAL_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(n) for p, n in POINT_NAMES.items() if p.startswith("VAL"))
    + r"|VAL0[1-8])\b",
    re.IGNORECASE | re.UNICODE,
)
_VALENCIA_RE = re.compile(r"\b(?:valencia|val[eè]ncia|horta sud)\b", re.IGNORECASE)


def _timeout(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return default


# --------------------------------------------------------------------- places


def forecast_places(question: str, context: dict | None = None) -> list[ForecastPoint]:
    """The watched places a question asks about, at most MAX_PLACES."""
    ctx = context or {}
    out: list[ForecastPoint] = []
    target = watch_target(question or "", ctx)
    if target:
        for ref in (*target["stations"], *target["points"]):
            if ref in FORECAST_BY_REF:
                out.append(FORECAST_BY_REF[ref])
    if not out:
        for m in _VAL_RE.finditer(question or ""):
            word = m.group(0).upper()
            pid = (
                word
                if word in FORECAST_BY_ID
                else next((p for p, n in POINT_NAMES.items() if n.upper() == word), None)
            )
            if pid in FORECAST_BY_ID:
                out.append(FORECAST_BY_ID[pid])
    if not out and _VALENCIA_RE.search(question or ""):
        ev = EVENTS["EMSR773"]
        out = [FORECAST_BY_ID[p] for p in (*ev.river_points, *ev.rain_points)]
    if not out:
        station = str(ctx.get("station") or "")
        pick = next((r for r in FORECAST_BY_REF if r.upper() == station.upper()), None)
        pid = ctx.get("point_id") or ctx.get("watch_point")
        if pick:
            out = [FORECAST_BY_REF[pick]]
        elif pid in FORECAST_BY_ID:
            out = [FORECAST_BY_ID[pid]]
    return list(dict.fromkeys(out))[:MAX_PLACES]


def _asked(state: FloodState) -> list[ForecastPoint]:
    request = state.get("request") or {}
    return forecast_places(str(request.get("question") or ""), request.get("context") or {})


def label(p: ForecastPoint) -> str:
    """How a claim names the place: the gauge shortname, the city, the town."""
    if p[1] == "gauge":
        return p[2]
    if p[1] == "valencia":
        return POINT_NAMES.get(p[0], p[3])
    return p[3]


def country(p: ForecastPoint) -> str:
    if p[1] == "gauge":
        return "DE"
    if p[1] == "valencia":
        return "ES"
    from floodsense_agents.watch import EU_POINTS

    return next((e[2] for e in EU_POINTS if e[0] == p[0]), "")


def pattern_event(p: ForecastPoint) -> str | None:
    if p[1] == "valencia":
        return "EMSR773"
    if p[1] == "gauge" and p[4] in RHINE_BASIN:
        return "EMSR517"
    return None


# ----------------------------------------------------------------------- SQL


def weather_sql(schema: str, point_id: str) -> str:
    h = HORIZON_H
    return (
        f"SELECT point_id, name, river, ROUND(SUM(CASE WHEN lead_h < {h} THEN precip_mm END), 1) "
        f"AS rain_{h}h_mm, ROUND(SUM(precip_mm), 1) AS rain_72h_mm, MAX(CASE WHEN lead_h < {h} "
        f"THEN precip_mm END) AS max_hour_{h}h_mm, MIN(ts_utc) AS from_utc, MAX(ts_utc) AS to_utc, "
        f"COUNT(precip_mm) AS hours FROM {schema}.weather_forecast WHERE point_id = "
        f"{sql_list([point_id])} GROUP BY point_id, name, river"
    )


def pattern_sql(event_id: str, point_id: str) -> tuple[str, tuple[str, ...]]:
    """The replay-seed aggregate: 48 h rain before the peak and the window's peak discharge."""
    pat, ev = PATTERNS[event_id], EVENTS[event_id]
    sql = (
        "SELECT point_id, ROUND(SUM(CASE WHEN ts_utc >= ? AND ts_utc < ? THEN rain_mm END), 1) "
        "AS rain_48h_mm, MAX(CASE WHEN ts_utc >= ? AND ts_utc < ? THEN rain_mm END) AS "
        "max_hour_mm, MAX(discharge_m3s) AS peak_discharge_m3s, COUNT(*) AS hours FROM "
        f"floodsense_seed.hazard_timeline WHERE point_id = {sql_list([point_id])} AND ts_utc "
        "BETWEEN ? AND ? GROUP BY point_id"
    )
    w = (pat["rain_from"], pat["rain_to"])
    return sql, (*w, *w, ev.window_from_utc, ev.window_to_utc)


# --------------------------------------------------------------- forecast_data


def make_forecast_data(deps: Deps):
    def forecast_data(state: FloodState) -> dict:
        t = time.time()
        s = settings.schema
        asked = _asked(state)
        jobs: list[tuple[str, tuple[str, ...] | None]] = []
        slots: list[tuple[str, str]] = []  # (point_id, role)
        for p in asked:
            jobs.append((weather_sql(s, p[0]), None))
            slots.append((p[0], "weather"))
            if p[1] == "gauge":
                jobs.append((gauge_latest_sql(s, stations=(p[2],)), None))
                slots.append((p[0], "level"))
            elif p[1] == "eu":
                jobs.append((quick._sql("eu", p[0], s), None))
                slots.append((p[0], "river"))
            else:
                jobs.append((quick._sql("point", p[0], s), None))
                slots.append((p[0], "river"))
        jobs.append(
            (
                f"SELECT dataset, source_url, publisher, licence, attribution, fetched_at FROM "
                f"{s}.provenance",
                None,
            )
        )
        *reads, prov = run_sql_parallel(deps.zetaris, jobs)
        used: list[Evidence] = []
        found: dict[str, dict[str, Any]] = {
            p[0]: {"id": p[0], "kind": p[1], "ref": p[2]} for p in asked
        }
        notes: list[str] = []
        for (pid, role), ev in zip(slots, reads):
            p = FORECAST_BY_ID[pid]
            if ev.error:
                notes.append(f"{pid} {role}: {ev.view} unavailable")
                continue
            row = _row(p, role, ev)
            if row is None:
                notes.append(f"{pid} {role}: no row")
                continue
            used.append(ev)
            found[pid][role] = ev.query_id
            notes.append(f"{pid} {role}: {ev.view} 1 row")
        out: dict = {
            "evidence": add_evidence(state, *used),
            "provenance": prov.rows_sample if not prov.error else [],
            "live_findings": {"forecast_places": list(found.values())},
            "trace": trace(
                state,
                "forecast_data",
                "; ".join(notes) or "no watched place in the question",
                lane="sql",
                started=t,
                evidence_ids=[e.query_id for e in used],
            ),
        }
        if not used:
            out["escalate"] = (
                "no forecast rows for the asked place ("
                + ("; ".join(notes) or "no watched place named")
                + ")"
            )
        return out

    return forecast_data


def _row(p: ForecastPoint, role: str, ev: Evidence) -> dict | None:
    """The row of this place only, with a value to state."""
    for r in ev.rows_sample:
        if role == "weather" and r.get("point_id") == p[0]:
            return r if quick._num(r.get(f"rain_{HORIZON_H}h_mm")) is not None else None
        if role == "level" and str(r.get("station") or "").upper() == p[2].upper():
            return r if quick._num(r.get("level_cm")) is not None else None
        if role == "river":
            kind = "eu" if p[1] == "eu" else "point"
            got = quick._own_row(kind, p[0], ev)
            if got is None:
                return None
            keys = (
                ("forecast_max_m3s", "discharge_m3s")
                if kind == "eu"
                else ("forecast_max_discharge_m3s", "past_max_discharge_m3s")
            )
            return got if any(quick._num(got.get(k)) is not None for k in keys) else None
    return None


def route_after_forecast_data(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "history"


# --------------------------------------------------------------------- history


def _memory_rows(memories: list[dict], p: ForecastPoint) -> list[dict]:
    """Recalled memories that name this place, its river or its gauge. Seeded ones labelled."""
    words = {label(p).lower(), p[3].lower(), p[4].lower(), p[2].lower()}
    rows = []
    for m in memories or []:
        if not isinstance(m, dict):
            continue
        text = str(m.get("content") or "")
        low = text.lower()
        if not any(w and re.search(rf"(?<!\w){re.escape(w)}(?!\w)", low) for w in words):
            continue
        seeded, reviewer = memory_origin(m)
        prov = m.get("provenance") if isinstance(m.get("provenance"), dict) else {}
        if _EMPTY_MEMORY.search(text):
            continue  # an approved run that said it could state nothing is no pattern
        rows.append(
            {
                "memory_id": m.get("memory_id"),
                "run_id": m.get("run_id"),
                "claim_id": m.get("claim_id"),
                "content": text[:300],
                "approved_at": prov.get("learned_at"),
                "reviewer": reviewer,
                "seeded": seeded,
            }
        )
    # Seeded demo memories first, then ones that state a figure.
    rows.sort(key=lambda r: (not r["seeded"], not re.search(r"\d", r["content"])))
    return rows


_EMPTY_MEMORY = re.compile(r"\bno (?:supporting )?evidence\b|\bcan(?:not|'t) be stated\b", re.I)


def make_history(deps: Deps):
    def history(state: FloodState) -> dict:
        t = time.time()
        asked = _asked(state)
        events = list(dict.fromkeys(e for e in (pattern_event(p) for p in asked) if e))
        notes: list[str] = []
        budget = _timeout("FORECAST_HISTORY_TIMEOUT_S", 10)
        # 1. replay seed: one aggregate per (event, pattern point)
        seed_jobs: list[tuple[str, str, str, tuple[str, ...]]] = []
        for p in asked:
            ev_id = pattern_event(p)
            if not ev_id:
                continue
            point = PATTERNS[ev_id]["point"] or p[0]
            if all(j[1] != point for j in seed_jobs):
                sql, params = pattern_sql(ev_id, point)
                seed_jobs.append((ev_id, point, sql, params))
        fut_seed = (
            _POOL.submit(run_sql_parallel, deps.zetaris, [(j[2], j[3]) for j in seed_jobs])
            if seed_jobs
            else None
        )
        # 2. RAG: one query per event, built from the first place of that event
        fut_docs: dict[str, Any] = {}
        if deps.retrieve_docs is not None:
            for ev_id in events:
                p = next(x for x in asked if pattern_event(x) == ev_id)
                q = f"{label(p)} flood: {EVENTS[ev_id].name}, rain before the peak"
                fut_docs[ev_id] = _POOL.submit(deps.retrieve_docs, q, 2, {"event_id": ev_id})
        else:
            notes.append("RAG off (FF_RAG_DOCS)")
        # 3. H-MEM recall per place
        fut_mem: dict[str, Any] = {}
        for p in asked:
            req = {"question": f"{label(p)} {p[4]} flood", "event_id": pattern_event(p)}
            fut_mem[p[0]] = _POOL.submit(deps.memory.recall, req)

        found: dict[str, Any] = {"patterns": [], "passages": [], "memories": []}
        extra: list[Evidence] = []
        if fut_seed is not None:
            try:
                reads = fut_seed.result(timeout=budget)
            except FutureTimeout:
                reads = []
                notes.append("replay seed over time")
            for (ev_id, point, _sql, _params), ev in zip(seed_jobs, reads):
                row = next((r for r in ev.rows_sample if r.get("point_id") == point), None)
                if ev.error or row is None or quick._num(row.get("rain_48h_mm")) is None:
                    notes.append(f"{ev_id} seed {point}: no row")
                    continue
                extra.append(ev)
                found["patterns"].append(
                    {"event_id": ev_id, "point": point, "query_id": ev.query_id}
                )
                notes.append(f"{ev_id} seed {point}: 1 row")
        for ev_id, fut in fut_docs.items():
            try:
                res = fut.result(timeout=budget)
            except FutureTimeout:
                notes.append(f"{ev_id} RAG over time")
                continue
            except Exception as e:  # noqa: BLE001 - a passage is optional evidence
                notes.append(f"{ev_id} RAG error: {str(e)[:120]}")
                continue
            if getattr(res, "error", None):
                notes.append(f"{ev_id} RAG error: {str(res.error)[:120]}")
                continue
            top = next((r for r in (res.citations or []) if _verified_raw(r)), None)
            if top is None:
                notes.append(f"{ev_id} RAG: no verified passage")
                continue
            found["passages"].append({"event_id": ev_id, "raw": top})
            notes.append(f"{ev_id} RAG: 1 passage")
        for p in asked:
            try:
                mems = fut_mem[p[0]].result(timeout=budget)
            except FutureTimeout:
                notes.append(f"{p[0]} H-MEM over time")
                continue
            except Exception as e:  # noqa: BLE001 - the engines never fail a run
                notes.append(f"{p[0]} H-MEM: {short(e)}")
                continue
            rows = _memory_rows(mems, p)[:1]
            if not rows:
                continue
            ev = Evidence(
                query_id=f"hmem-{uuid.uuid4().hex[:12]}",
                view="hmem.recall",
                sql=f"POST /hmem/recall {{query: '{label(p)} {p[4]} flood'}}",
                rows_sample=rows,
                row_count=len(rows),
                executed_at_utc=now_utc(),
                source="engines",
            )
            extra.append(ev)
            found["memories"].append({"point_id": p[0], "query_id": ev.query_id})
            seeded = " (demo seed)" if rows[0]["seeded"] else ""
            notes.append(f"{p[0]} H-MEM: 1 approved memory{seeded}")
        lf = dict(state.get("live_findings") or {})
        lf["forecast_history"] = found
        return {
            "evidence": add_evidence(state, *extra),
            "live_findings": lf,
            "trace": trace(
                state,
                "history",
                "; ".join(notes) or "no past pattern for these places",
                lane="sql",
                started=t,
                evidence_ids=[e.query_id for e in extra],
            ),
        }

    return history


# ------------------------------------------------------------- forecast_answer

Built = tuple[str, list[float]]


def _hhmm(ts: Any) -> str | None:
    return quick._hhmm(ts)


def weather_claim(p: ForecastPoint, row: dict) -> tuple[Built, float, float | None]:
    r48 = quick._num(row.get(f"rain_{HORIZON_H}h_mm")) or 0.0
    r72 = quick._num(row.get("rain_72h_mm"))
    hour = quick._num(row.get(f"max_hour_{HORIZON_H}h_mm"))
    text = (
        f"{label(p)}: forecast precipitation for the next {HORIZON_H} hours is {quick._fmt(r48)} mm"
    )
    nums = [r48]
    if hour is not None:
        text += f", wettest hour {quick._fmt(hour)} mm"
        nums.append(hour)
    if r72 is not None:
        text += f" ({quick._fmt(r72)} mm over 72 hours)"
        nums.append(r72)
    at = _hhmm(row.get("from_utc"))
    text += f"; DWD ICON model via Open-Meteo{', from ' + at + ' UTC' if at else ''} (weather_forecast)."
    return (text, nums), r48, hour


def river_claim(p: ForecastPoint, row: dict) -> tuple[Built, str] | None:
    """(claim, status) from the GloFAS discharge forecast. eu_watch or hazard_now."""
    if p[1] == "eu":
        built = quick.eu_claim(row)
        if not built:
            return None
        text, nums, _lead, _sev = built
        band = str(row.get("band") or "unknown")
        st = WARNING if band == "above" else WATCH if band == "near" else NORMAL
        return (text, nums), st
    fmax = quick._num(row.get("forecast_max_discharge_m3s"))
    past = quick._num(row.get("past_max_discharge_m3s"))
    if fmax is None and past is None:
        return None
    nums: list[float] = []
    text = f"{label(p)}: GloFAS model discharge"
    if past is not None:
        text += f" peaked at {quick._fmt(past)} m3/s over the past days"
        nums.append(past)
    st = NORMAL
    if fmax is not None:
        crosses = fmax >= DISCHARGE_LINE
        st = WARNING if crosses else NORMAL
        text += (
            f"{' and' if past is not None else ''} peaks at {quick._fmt(fmax)} m3/s in the forecast "
            f"window, {'above' if crosses else 'under'} FloodSense's {DISCHARGE_LINE:g} m3/s anomaly line"
        )
        nums.append(fmax)
    else:
        text += "; no discharge forecast in the live window"
    return (text + " (hazard_now, model, not an official warning).", nums), st


def level_claim(p: ForecastPoint, row: dict) -> tuple[Built, str] | None:
    level = quick._num(row.get("level_cm"))
    if level is None:
        return None
    at = _hhmm(row.get("ts_utc"))
    age = hours_between(now_utc(), str(row.get("ts_utc") or ""))
    stale = age is not None and age > GAUGE_STALE_H
    text = f"{p[2]} ({row.get('water') or p[4]}) gauge: level {quick._fmt(level)} cm"
    text += f" at {at} UTC" if at else ""
    text += f" (stale: older than {GAUGE_STALE_H} h)" if stale else ""
    nums = [level]
    st = NORMAL
    th = gauge_threshold(row)
    if th:
        mhw = th[1]
        nums.append(mhw)
        if level >= mhw:
            st, where = WARNING, "above"
        elif level >= 0.8 * mhw:
            st, where = WATCH, "near"
        else:
            where = "below"
        text += f", {where} the station's mean high water (MHW) of {quick._fmt(mhw)} cm"
    trend = quick._num(row.get("trend_cm_h"))
    prev = quick._num(row.get("prev_cm"))
    if trend is not None:
        word = "rising" if trend > 0 else "falling" if trend < 0 else "steady"
        text += f"; trend {quick._fmt(trend)} cm/h ({word})"
        nums.append(trend)
    elif prev is not None and row.get("prev_utc") != row.get("ts_utc"):
        word = "rising" if level > prev else "falling" if level < prev else "steady"
        text += f"; {word} from {quick._fmt(prev)} cm about three hours earlier"
        nums.append(prev)
    return (text + " (PEGELONLINE).", nums), st


def pattern_claim(p: ForecastPoint, ev_id: str, row: dict, rain48: float) -> Built | None:
    past = quick._num(row.get("rain_48h_mm"))
    peak = quick._num(row.get("peak_discharge_m3s"))
    if past is None:
        return None
    pat = PATTERNS[ev_id]
    where = POINT_NAMES.get(str(row.get("point_id")), str(row.get("point_id")))
    text = (
        f"Past pattern: before the {pat['label']}, rain over 48 hours ({pat['days']}) reached "
        f"{quick._fmt(past)} mm at {where}"
    )
    nums = [past]
    if peak is not None:
        text += f" and modelled discharge peaked at {quick._fmt(peak)} m3/s"
        nums.append(peak)
    text += (
        f" (Open-Meteo historical weather and GloFAS, FloodSense replay seed); the forecast for "
        f"the next {HORIZON_H} hours at {label(p)} is {quick._fmt(rain48)} mm."
    )
    nums.append(rain48)
    return text, nums


def _rain_status(r48: float, hour: float | None, past: float | None) -> str:
    if r48 >= RAIN_WARN_MM or (hour is not None and hour >= HOUR_WARN_MM):
        return WARNING
    if past and r48 >= past:
        return WARNING
    if r48 >= RAIN_WATCH_MM or (hour is not None and hour >= HOUR_WATCH_MM):
        return WATCH
    if past and r48 >= 0.5 * past:
        return WATCH
    return NORMAL


def _ok_place_words() -> set[str]:
    from floodsense_agents.router import PLACES
    from floodsense_agents.watch import FORECAST_POINTS

    words = {w.lower() for w in place_words()} | set(PLACES)
    words |= {n.lower() for n in POINT_NAMES.values()}
    for p in FORECAST_POINTS:
        words |= {w.lower() for w in re.findall(r"[^\W\d_]{3,}", f"{p[2]} {p[3]} {p[4]}")}
    words -= {"river", "the", "and", "bad", "gauge"}
    return words


def outlook_ok(outlook: str, claims: list[Claim]) -> tuple[bool, str]:
    """(ok, why): no number and no place the claims do not carry; at most two sentences."""
    text = " ".join((outlook or "").split())
    if not text:
        return False, "empty"
    if len(text) > 400:
        return False, "too long"
    if len(re.findall(r"[.!?](?:\s|$)", text)) > 2:
        return False, "more than two sentences"
    body = " ".join(c.text for c in claims)
    have = numbers_in(body)
    for n in numbers_in(text):
        if not any(abs(n - h) < 1e-9 for h in have):
            return False, f"names the number {n:g}, which no claim states"
    low = body.lower()
    known = _ok_place_words()
    for w in re.findall(r"[^\W\d_][\w'.-]*", text):
        lw = w.lower().strip(".'")
        if lw in known and lw not in low:
            return False, f"names '{w}', which no claim names"
    if re.search(r"\bofficial warning\b", text, re.I) and not re.search(
        r"\bnot an official", text, re.I
    ):
        return False, "presents itself as an official warning"
    return True, "kept"


def _outlook(
    deps: Deps, state: FloodState, status: str, claims: list[Claim]
) -> tuple[str, str | None, str]:
    question = str((state.get("request") or {}).get("question") or "")
    facts = "\n".join(f"- {c.text}" for c in claims)
    user = f"QUESTION: {question}\nSTATUS: {status}\nFACTS:\n{facts}"
    budget = _timeout("FORECAST_OUTLOOK_TIMEOUT_S", 25)
    fut = submit_with_deadline(_POOL, budget, deps.llm.complete, "fast", OUTLOOK_SYSTEM, user)
    try:
        text, model_id = fut.result(timeout=budget)
    except FutureTimeout:
        return "", None, "outlook dropped: fast lane over time"
    except Exception as e:  # noqa: BLE001 - the claims stand without an outlook
        return "", None, f"outlook dropped: fast lane failed ({type(e).__name__})"
    try:
        cand = str(parse_json(text).get("outlook") or "").strip()
    except Exception:  # noqa: BLE001
        cand = ""
    ok, why = outlook_ok(cand, claims)
    if not ok:
        return (
            "",
            model_id,
            f"outlook dropped: {why}" if cand else "outlook dropped: no outlook in the reply",
        )
    return " ".join(cand.split()), model_id, "outlook kept"


def make_forecast_answer(deps: Deps):
    def forecast_answer(state: FloodState) -> dict:
        t = time.time()
        prov = state.get("provenance") or []
        evidence = {q: Evidence(**e) for q, e in (state.get("evidence") or {}).items()}
        lf = state.get("live_findings") or {}
        hist = lf.get("forecast_history") or {}
        claims: list[Claim] = []
        data_claims: list[Claim] = []
        extra: list[Evidence] = []
        statuses: list[tuple[str, str, str]] = []  # (status, place, reason)
        gaps: list[str] = []

        def add(text: str, nums: list[float], evs: list[Evidence], data: bool = True) -> Claim:
            cid = f"F{len(claims) + 1}"
            cits: list[Citation] = []
            for n, ev in enumerate(evs, start=1):
                cits += cite(cid, ev, prov, n)
            c = Claim(
                claim_id=cid,
                text=text,
                kind="number" if nums else "fact",
                numbers=nums,
                citations=cits,
            )
            claims.append(c)
            if data:
                data_claims.append(c)
            return c

        for place in lf.get("forecast_places") or []:
            p = FORECAST_BY_ID.get(place["id"])
            if p is None:
                continue
            rain48, hour = None, None
            wev = evidence.get(place.get("weather") or "")
            if wev is not None:
                row = _row(p, "weather", wev)
                if row is not None:
                    (text, nums), rain48, hour = weather_claim(p, row)
                    add(text, nums, [wev])
            else:
                gaps.append(f"no weather forecast row for {label(p)}")
            rev = evidence.get(place.get("river") or "")
            if rev is not None and (row := _row(p, "river", rev)) is not None:
                got = river_claim(p, row)
                if got:
                    (text, nums), st = got
                    add(text, nums, [rev])
                    statuses.append((st, label(p), "river forecast"))
            elif p[1] == "gauge":
                gaps.append(
                    f"FloodSense holds no river discharge forecast for the {p[2]} gauge; the outlook "
                    f"rests on the rain forecast and the current level"
                )
            lev = evidence.get(place.get("level") or "")
            if lev is not None and (row := _row(p, "level", lev)) is not None:
                got = level_claim(p, row)
                if got:
                    (text, nums), st = got
                    add(text, nums, [lev])
                    statuses.append((st, label(p), "current level"))
            past = None
            ev_id = pattern_event(p)
            pat = (
                next(
                    (
                        x
                        for x in hist.get("patterns") or []
                        if x["event_id"] == ev_id
                        and x["point"] == (PATTERNS[ev_id]["point"] or p[0])
                    ),
                    None,
                )
                if ev_id
                else None
            )
            if pat and rain48 is not None and wev is not None:
                sev = evidence.get(pat["query_id"])
                srow = next(
                    (
                        r
                        for r in (sev.rows_sample if sev else [])
                        if r.get("point_id") == pat["point"]
                    ),
                    None,
                )
                built = pattern_claim(p, ev_id, srow, rain48) if srow else None
                if built:
                    add(built[0], built[1], [sev, wev])
                    past = quick._num(srow.get("rain_48h_mm"))
            if rain48 is not None:
                statuses.append((_rain_status(rain48, hour, past), label(p), "rain forecast"))
            for mem in hist.get("memories") or []:
                if mem["point_id"] != p[0]:
                    continue
                mev = evidence.get(mem["query_id"])
                if not mev or not mev.rows_sample:
                    continue
                m = mev.rows_sample[0]
                tag = "demo seed, " if m.get("seeded") else ""
                who = f"approved by {m['reviewer']}" if m.get("reviewer") else "approved"
                excerpt = " ".join(str(m.get("content") or "").split())[:200]
                add(
                    f'Approved memory (H-MEM, {tag}{who}) for {label(p)}: "{excerpt}" '
                    f"(context from an earlier run, not a measurement).",
                    [],
                    [mev],
                    data=False,
                )
        for passage in hist.get("passages") or []:
            raw = passage["raw"]
            c = Claim(claim_id=f"F{len(claims) + 1}", text=_doc_text(raw), kind="fact")
            rows_for_q: dict[str, list[dict]] = {}
            _cite_passage(c, raw, 1, rows_for_q)
            claims.append(c)
            for qid, rows in rows_for_q.items():
                extra.append(
                    Evidence(
                        query_id=qid,
                        view="PGVECTOR_RAG.chunks",
                        sql=_DOC_SQL,
                        rows_sample=rows[:20],
                        row_count=len(rows),
                        executed_at_utc=now_utc(),
                    )
                )
        if not data_claims:
            return {
                "escalate": "the forecast rows hold nothing to state",
                "trace": trace(
                    state,
                    "forecast_answer",
                    "no forecast value in the rows",
                    lane="none",
                    started=t,
                ),
            }
        worst = max((s for s, _, _ in statuses), key=lambda s: _RANK[s], default=NORMAL)
        why = "; ".join(
            f"{place}: {reason}" for s, place, reason in statuses if s == worst and worst != NORMAL
        )
        places = list(
            dict.fromkeys(
                label(FORECAST_BY_ID[x["id"]])
                for x in lf.get("forecast_places") or []
                if x["id"] in FORECAST_BY_ID
            )
        )
        countries = list(
            dict.fromkeys(
                country(FORECAST_BY_ID[x["id"]])
                for x in lf.get("forecast_places") or []
                if x["id"] in FORECAST_BY_ID
            )
        )
        follow = (
            "; ".join(OFFICIAL[c] for c in countries if c in OFFICIAL)
            or "your national weather and flood service"
        )
        disclaimer = f"This is a model outlook, not an official warning; follow {follow}."
        status_line = (
            f"Status: {worst} for {', '.join(places)} over the next {HORIZON_H} hours "
            f"(FloodSense screening{': ' + why if why else ''}; not an official warning)."
        )
        outlook, model_id, note = _outlook(deps, state, worst, data_claims)
        parts = [status_line]
        if outlook:
            parts.append(f"Outlook (model-written): {outlook}")
        parts += [c.text for c in claims]
        parts += [g[0].upper() + g[1:] + "." for g in gaps]
        parts.append(disclaimer)
        return {
            "claims": [c.model_dump() for c in claims],
            "evidence": add_evidence(state, *extra) if extra else state.get("evidence") or {},
            "summary": " ".join(parts),
            "forecast": {
                "status": worst,
                "status_reason": why or "no screening cut reached",
                "places": places,
                "horizon_h": HORIZON_H,
                "outlook": outlook or None,
                "outlook_label": "Outlook (model-written)" if outlook else None,
                "outlook_model_id": model_id if outlook else None,
                "outlook_note": note,
                "gaps": gaps,
                "disclaimer": disclaimer,
                "attribution": "Weather data by Open-Meteo.com, model DWD ICON",
            },
            "trace": trace(
                state,
                "forecast_answer",
                f"{len(claims)} deterministic claims; status {worst}; {note}",
                lane="fast" if model_id else "none",
                model_id=model_id or "deterministic",
                started=t,
                evidence_ids=[q for c in claims for q in (x.query_id for x in c.citations) if q],
            ),
        }

    return forecast_answer


def route_after_answer(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "forecast_judge"
