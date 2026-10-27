"""The quick lane: a live reading answered in one short agent path.

    scope ─┬─ in scope, lane=quick → live_watch → quick_answer → quick_judge ─┬─ pass → END (answered)
           │                                                                  └─ flag / no data → escalate → watchers
           └─ declined → END (a decline is never overridden)

live_watch resolves the asked places first, then reads one Zetaris query per
place, in parallel, so every row belongs to exactly one place:

  gauge station   live.gauge_latest_sql(schema, stations=(station,)): latest
                  PEGELONLINE level, the trend baseline, MHW when the view has it
  EU model point  {schema}.eu_watch WHERE point_id = '<id>' (GloFAS model cell)
  event point     {schema}.hazard_now past/forecast summary WHERE point_id = '<id>'

Places come from watch.watch_target (city first, then river; the user's
selected station or watch point), else the event's point names in the
question, else every point of the event. At most MAX_PLACES are read.

quick_answer builds every claim deterministically, one per place, from that
place's row with a fixed template, and cites only that place's query. The
numbers a claim states (claim.numbers) are cells of that row. One fast-lane
call may write a one-sentence lead. The lead is not a claim: it is the run's
summary, and it is dropped unless every number in it appears in a claim and
every place word in it is named by a claim.

quick_judge runs judge.evaluate with no model: per claim, a citation exists,
its query returned rows, and every number in claim.numbers is a cell of the
cited rows (NUMERIC_TOLERANCE). A claim with a failed check is flagged.

No rows, or any flag, escalates: the run goes on to watchers and the full lane,
and the trace says why ("escalated: ...").
"""

from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from floodsense_agents.events import POINT_NAMES, point_label
from floodsense_agents.live import (
    LIVE_ROWS,
    gauge_latest_sql,
    gauge_threshold,
    live_points,
)
from floodsense_agents.models import Claim, Evidence
from floodsense_agents.nightshift import parse_json
from floodsense_agents.nodes import judge as judge_node
from floodsense_agents.nodes.investigator import cite, numbers_in
from floodsense_agents.settings import settings
from floodsense_agents.state import Deps, FloodState, add_evidence, trace
from floodsense_agents.watch import EU_POINTS, place_words, sql_list, watch_target
from floodsense_agents.zetaris import run_sql_parallel

log = logging.getLogger("floodsense.quick")

QUICK, FULL = "quick", "full"
MAX_PLACES = 6
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="quick-lane")
_EU = {p[0]: p for p in EU_POINTS}

SYSTEM = """TASK: quick_lead
Write ONE plain-language sentence that leads into the facts below for a member of the public.
Use only places and numbers that appear in the facts; add no new number, place or advice.
Answer with JSON only: {"lead": "..."}"""


def _timeout_s() -> float:
    try:
        return float(os.environ.get("QUICK_LANE_TIMEOUT_S") or 15)
    except ValueError:
        return 15.0


def route_after_scope(state: FloodState) -> str:
    """scope's router with the quick lane. A decline always ends the run."""
    if not (state.get("scope") or {}).get("in_scope", True):
        return "declined"
    return "live_watch" if state.get("lane") == QUICK else "watchers"


def places(state: FloodState) -> list[tuple[str, str]]:
    """[(kind, id)] the question asks about: gauge, eu or point."""
    request = state.get("request") or {}
    question = str(request.get("question") or "")
    target = watch_target(question, request.get("context") or {})
    if target:
        out = [("gauge", s) for s in target["stations"]] + [("eu", p) for p in target["points"]]
        return out[:MAX_PLACES]
    pts = live_points(state.get("event") or {})
    named = [
        p
        for p in pts
        if p in POINT_NAMES and re.search(rf"\b{re.escape(POINT_NAMES[p])}\b", question, re.I)
    ]
    ctx_point = (request.get("context") or {}).get("point_id")
    if ctx_point in pts and not named:
        named = [ctx_point]
    return [("point", p) for p in (named or list(pts))][:MAX_PLACES]


def _sql(kind: str, ident: str, s: str) -> str:
    if kind == "gauge":
        return gauge_latest_sql(s, stations=(ident,))
    if kind == "eu":
        return (
            f"SELECT point_id, name, country, river, discharge_m3s, forecast_max_m3s, "
            f"past30_median_m3s, band, basis, as_of_date FROM {s}.eu_watch WHERE point_id = "
            f"{sql_list([ident])}"
        )
    return (
        f"SELECT point_id, MAX(CASE WHEN horizon = 'forecast' THEN discharge_m3s END) AS "
        f"forecast_max_discharge_m3s, MAX(CASE WHEN horizon = 'forecast' THEN rain_mm END) AS "
        f"forecast_max_rain_mm, MAX(CASE WHEN horizon = 'past' THEN discharge_m3s END) AS "
        f"past_max_discharge_m3s FROM {s}.hazard_now WHERE point_id = {sql_list([ident])} AND "
        f"{LIVE_ROWS} GROUP BY point_id"
    )


def _own_row(kind: str, ident: str, ev: Evidence) -> dict | None:
    """The row of this place only: matched on the name / river / point_id columns."""
    for r in ev.rows_sample:
        if kind == "gauge" and str(r.get("station") or "").upper() == ident.upper():
            return r
        if kind == "eu":
            p = _EU.get(ident)
            if (
                r.get("point_id") == ident
                and p
                and str(r.get("name") or "").lower() == p[1].lower()
                and str(r.get("river") or "").lower() == p[3].lower()
            ):
                return r
        if kind == "point" and r.get("point_id") == ident:
            return r
    return None


def make_live_watch(deps: Deps):
    def live_watch(state: FloodState) -> dict:
        t = time.time()
        s = settings.schema
        asked = places(state)
        jobs = [(_sql(k, i, s), None) for k, i in asked]
        jobs.append(
            (
                f"SELECT dataset, source_url, publisher, licence, attribution, fetched_at FROM "
                f"{s}.provenance",
                None,
            )
        )
        *reads, prov = run_sql_parallel(deps.zetaris, jobs)
        notes: list[str] = []
        used: list[Evidence] = []
        found: list[dict] = []
        for (kind, ident), ev in zip(asked, reads):
            if ev.error:
                notes.append(f"{ident}: {ev.view} unavailable")
                continue
            row = _own_row(kind, ident, ev)
            if row is None:
                notes.append(f"{ident}: no live row")
                continue
            used.append(ev)
            found.append({"kind": kind, "id": ident, "query_id": ev.query_id})
            notes.append(f"{ident}: {ev.view} 1 row")
        out: dict = {
            "evidence": add_evidence(state, *used),
            "provenance": prov.rows_sample if not prov.error else [],
            "live_findings": {"quick_places": found},
            "trace": trace(
                state,
                "live_watch",
                "; ".join(notes) or "no place to read",
                lane="sql",
                started=t,
                evidence_ids=[e.query_id for e in used],
            ),
        }
        if not used:
            out["escalate"] = (
                "no live rows for the asked place (" + ("; ".join(notes) or "none") + ")"
            )
        return out

    return live_watch


def route_after_live_watch(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "quick_answer"


def _num(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _fmt(v: float) -> str:
    return f"{v:g}" if abs(v) >= 100 or v == int(v) else f"{v:.1f}"


def gauge_claim(row: dict) -> tuple[str, list[float]] | None:
    level = _num(row.get("level_cm"))
    if level is None:
        return None
    station, water = row.get("station"), row.get("water")
    text = f"{station} ({water}) gauge: latest level {_fmt(level)} cm"
    nums = [level]
    th = gauge_threshold(row)
    if th:
        mhw = th[1]
        band = "above" if level >= mhw else "near" if level >= 0.8 * mhw else "below"
        text += f", {band} the station's mean high water (MHW) of {_fmt(mhw)} cm"
        nums.append(mhw)
    prev = _num(row.get("prev_cm"))
    # One reading only: the baseline is the reading itself, so there is no trend.
    if prev is not None and row.get("prev_utc") != row.get("ts_utc"):
        trend = "rising" if level > prev else "falling" if level < prev else "steady"
        text += f"; {trend} from {_fmt(prev)} cm about three hours earlier"
        nums.append(prev)
    return text + " (PEGELONLINE).", nums


def eu_claim(row: dict) -> tuple[str, list[float]] | None:
    q, fmax, med = (
        _num(row.get(k)) for k in ("discharge_m3s", "forecast_max_m3s", "past30_median_m3s")
    )
    if q is None and fmax is None:
        return None
    text = f"{row.get('name')} ({row.get('river')}, {row.get('country')}): model"
    nums: list[float] = []
    if q is not None:
        text += f" discharge {_fmt(q)} m3/s today"
        nums.append(q)
    if fmax is not None:
        text += f", forecast maximum {_fmt(fmax)} m3/s"
        nums.append(fmax)
    if med is not None:
        text += f" against a past-month median of {_fmt(med)} m3/s"
        nums.append(med)
    band = row.get("band") or "unknown"
    return text + f"; band {band} (GloFAS model cell value, not an official warning).", nums


def point_claim(row: dict) -> tuple[str, list[float]] | None:
    fmax, rain = _num(row.get("forecast_max_discharge_m3s")), _num(row.get("forecast_max_rain_mm"))
    if fmax is None and rain is None:
        return None
    text = f"{point_label(str(row.get('point_id')))}: in the live forecast window"
    nums: list[float] = []
    if fmax is not None:
        text += f" discharge peaks at {_fmt(fmax)} m3/s"
        nums.append(fmax)
    if rain is not None:
        text += f"{',' if fmax is not None else ''} hourly rain peaks at {_fmt(rain)} mm"
        nums.append(rain)
    return text + " (GloFAS / Open-Meteo, hazard_now).", nums


_TEMPLATES = {"gauge": gauge_claim, "eu": eu_claim, "point": point_claim}


def build_claims(state: FloodState) -> list[Claim]:
    """One claim per place, from that place's row, citing only that place's query."""
    prov = state.get("provenance") or []
    claims: list[Claim] = []
    for place in (state.get("live_findings") or {}).get("quick_places") or []:
        raw = (state.get("evidence") or {}).get(place["query_id"])
        if not raw:
            continue
        ev = Evidence(**raw)
        row = _own_row(place["kind"], place["id"], ev)
        built = _TEMPLATES[place["kind"]](row) if row else None
        if not built:
            continue
        text, nums = built
        cid = f"Q{len(claims) + 1}"
        claims.append(
            Claim(
                claim_id=cid,
                text=text,
                kind="number",
                numbers=nums,
                citations=cite(cid, ev, prov, 1),
            )
        )
    return claims


_PLACE_WORDS = None


def _place_words() -> set[str]:
    global _PLACE_WORDS
    if _PLACE_WORDS is None:
        from floodsense_agents.router import PLACES

        words = {w.lower() for w in place_words()} | set(PLACES)
        words |= {n.lower() for n in POINT_NAMES.values()}
        _PLACE_WORDS = words
    return _PLACE_WORDS


def lead_ok(lead: str, claims: list[Claim]) -> bool:
    """No number and no place word the claims do not carry."""
    body = " ".join(c.text for c in claims)
    have = numbers_in(body)
    for n in numbers_in(lead):
        if not any(abs(n - h) < 1e-9 for h in have):
            return False
    low = body.lower()
    for w in re.findall(r"[^\W\d_][\w'.-]*", lead):
        if w.lower() in _place_words() and w.lower() not in low:
            return False
    return bool(lead.strip()) and len(lead) <= 300 and lead.count(".") <= 2


def make_answer(deps: Deps):
    def quick_answer(state: FloodState) -> dict:
        t = time.time()
        claims = build_claims(state)
        if not claims:
            return {
                "escalate": "the live rows hold no reading to state",
                "trace": trace(
                    state, "quick_answer", "no reading in the live rows", lane="none", started=t
                ),
            }
        facts = "\n".join(f"- {c.text}" for c in claims)
        question = str((state.get("request") or {}).get("question") or "")
        lead, model_id, note = "", None, "lead dropped"
        fut = _POOL.submit(
            deps.llm.complete, "fast", SYSTEM, f"QUESTION: {question}\nFACTS:\n{facts}"
        )
        try:
            text, model_id = fut.result(timeout=_timeout_s())
            cand = str(parse_json(text).get("lead") or "").strip()
            if lead_ok(cand, claims):
                lead, note = cand, "lead kept"
            elif cand:
                note = "lead dropped: names a number or place the claims do not"
        except FutureTimeout:
            note = "lead dropped: fast lane over time"
        except Exception as e:  # noqa: BLE001 - the claims stand without a lead
            note = f"lead dropped: fast lane failed ({type(e).__name__})"
        summary = lead or " ".join(c.text for c in claims)
        return {
            "claims": [c.model_dump() for c in claims],
            "summary": summary,
            "trace": trace(
                state,
                "quick_answer",
                f"{len(claims)} template claims, one per place; {note}",
                lane="fast" if model_id else "none",
                model_id=model_id,
                started=t,
                evidence_ids=[q for c in claims for q in (x.query_id for x in c.citations) if q],
            ),
        }

    return quick_answer


def route_after_answer(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "quick_judge"


def quick_judge(state: FloodState) -> dict:
    """judge.evaluate with no model. A pass ends the run as answered."""
    t = time.time()
    claims = [Claim(**c) for c in state.get("claims") or []]
    evidence = {q: Evidence(**e) for q, e in (state.get("evidence") or {}).items()}
    scores, rep = judge_node.evaluate(claims, evidence, None)
    unmatched = [
        s.claim_id
        for s in scores
        if not s.numbers_match or not s.coverage or not s.citation_faithful
    ]
    flagged = sorted(set(rep.flagged_claim_ids) | set(unmatched))
    ok = rep.passes and not flagged
    out = {
        "judge": [s.model_dump() for s in scores],
        "judge_summary": rep.model_dump(),
        "trace": trace(
            state,
            "judge",
            f"{'PASS' if ok else 'FLAG'} overall={rep.overall:.2f} "
            f"hallucination={rep.hallucination_rate:.0%} coverage={rep.citation_coverage:.0%} "
            f"numbers={rep.numeric_accuracy:.0%} flagged={flagged or '-'}",
            lane="none",
            model_id=rep.model_id,
            started=t,
        ),
    }
    if ok:
        out["status"] = "answered"
    else:
        out["escalate"] = f"judge flagged {', '.join(flagged) or 'the answer'}"
    return out


def route_after_quick_judge(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "done"


def escalate(state: FloodState) -> dict:
    """Hand the run to the full lane and say why on the trace."""
    why = state.get("escalate") or "quick lane could not answer"
    return {
        "lane": FULL,
        "router_reason": f"{state.get('router_reason') or 'chose quick'}; escalated: {why}",
        "escalate": None,
        "claims": [],
        "judge": [],
        "judge_summary": {},
        "summary": "",
        "status": "running",
        "trace": trace(state, "router", f"escalated: {why}; running the full lane", lane="none"),
    }


def route_after_escalate(state: FloodState) -> str:
    """Never run the full lane on a declined question: end with the decline."""
    return "watchers" if (state.get("scope") or {}).get("in_scope", True) else "declined"
