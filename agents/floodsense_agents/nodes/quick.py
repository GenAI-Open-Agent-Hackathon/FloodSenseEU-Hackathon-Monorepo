"""The quick lane: a live reading answered in one short agent path.

    scope -> live_watch -> quick_answer -> quick_judge ─┬─ pass -> END (status answered)
                                                        └─ flag / no data -> escalate -> watchers (full lane)

live_watch reads the live views through Zetaris, in parallel: the latest
gauge_levels reading per station, a per-point hazard_now summary (past and
forecast rows only), and floodsense.eu_watch when the warehouse has it (a
missing view is noted, never an error of the run). quick_answer is one
fast-lane call that writes 2-4 plain claims, each citing a query_id of those
reads. quick_judge runs the Judge's deterministic checks (judge.evaluate with
no model), so a number not in its cited rows fails exactly as on the full lane.

Anything flagged, missing or failed escalates: the run continues on the full
lane, and the trace says why ("escalated: ...").
"""

from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from floodsense_agents.live import LIVE_ROWS, gauge_latest_sql, points_sql
from floodsense_agents.models import Claim, Evidence
from floodsense_agents.nightshift import parse_json
from floodsense_agents.nodes import judge as judge_node
from floodsense_agents.nodes.investigator import cite, cited_numbers, numbers_in
from floodsense_agents.prompts import rows_block
from floodsense_agents.settings import settings
from floodsense_agents.state import Deps, FloodState, add_evidence, trace
from floodsense_agents.zetaris import run_sql_parallel

log = logging.getLogger("floodsense.quick")

QUICK, FULL = "quick", "full"
MAX_CLAIMS = 4
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="quick-lane")

SYSTEM = """TASK: quick_answer
You answer one live flood question for FloodSense EU from the Zetaris rows below.
Write 2 to 4 short plain-language claims. Every claim cites the query_id(s) of the rows it
uses, and every number in a claim is copied from those rows (same unit, no rounding beyond
one decimal). If the rows do not answer the question, return {"claims": []}.
Answer with JSON only:
{"claims": [{"text": "...", "query_ids": ["<query_id>"]}]}"""


def _timeout_s() -> float:
    try:
        return float(os.environ.get("QUICK_LANE_TIMEOUT_S") or 20)
    except ValueError:
        return 20.0


def route_after_scope(state: FloodState) -> str:
    """scope's router with the quick lane. Full-lane routing is unchanged."""
    verdict = state.get("scope") or {}
    if state.get("lane") == QUICK:
        # An unknown place (no event holds it) may still be in eu_watch.
        if verdict.get("in_scope", True) or verdict.get("elsewhere") is None:
            return "live_watch"
    return "watchers" if verdict.get("in_scope", True) else "declined"


def _words(state: FloodState) -> set[str]:
    q = str((state.get("request") or {}).get("question") or "")
    words = {w.lower() for w in re.findall(r"[^\W\d_]{3,}", q)}
    ctx = (state.get("request") or {}).get("context") or {}
    for key in ("station", "place"):
        if ctx.get(key):
            words.add(str(ctx[key]).lower())
    return words


def _mentions(row: dict, words: set[str]) -> bool:
    return any(isinstance(v, str) and v.lower() in words for v in row.values())


def make_live_watch(deps: Deps):
    def live_watch(state: FloodState) -> dict:
        t = time.time()
        s = settings.schema
        mode = (state.get("mode") or {}).get("mode")
        jobs = [
            (gauge_latest_sql(s), None),
            (
                f"SELECT point_id, MAX(CASE WHEN horizon = 'past' THEN discharge_m3s END) AS "
                f"past_max_discharge_m3s, MAX(CASE WHEN horizon = 'forecast' THEN discharge_m3s "
                f"END) AS forecast_max_discharge_m3s, MAX(CASE WHEN horizon = 'forecast' THEN "
                f"rain_mm END) AS forecast_max_rain_mm, MAX(warning_level) AS warning_level FROM "
                f"{s}.hazard_now WHERE point_id IN ({points_sql(state['event'])}) AND {LIVE_ROWS} "
                f"GROUP BY point_id ORDER BY forecast_max_discharge_m3s DESC",
                None,
            ),
            (f"SELECT * FROM {s}.eu_watch", None),
            (
                f"SELECT dataset, source_url, publisher, licence, attribution, fetched_at FROM "
                f"{s}.provenance",
                None,
            ),
        ]
        gauges, hazard, eu, prov = run_sql_parallel(deps.zetaris, jobs)
        words = _words(state)
        declined = (state.get("scope") or {}).get("in_scope") is False
        notes: list[str] = []
        used: list[Evidence] = []
        for name, ev in (("gauge_levels", gauges), ("hazard_now", hazard), ("eu_watch", eu)):
            if ev.error:
                # eu_watch may not exist yet (feat/eu-live-watch). A failed read is
                # left out of the evidence, so it neither backs a claim nor reads as a hole.
                notes.append(f"{name} unavailable")
                continue
            if ev.row_count == 0:
                notes.append(f"{name} 0 rows")
                continue
            # eu_watch spans Europe, and a place no event holds is only answered
            # from rows that name it.
            if (name == "eu_watch" or declined) and not any(
                _mentions(r, words) for r in ev.rows_sample
            ):
                notes.append(f"{name} has no row for the place asked")
                continue
            used.append(ev)
            notes.append(f"{name} {ev.row_count} rows")
        out: dict = {
            "evidence": add_evidence(state, *used),
            "provenance": prov.rows_sample if not prov.error else [],
            "live_findings": {"quick_query_ids": [e.query_id for e in used]},
        }
        missing = not used
        if missing and declined:
            # Nothing live about a place no event holds: the scope decline stands.
            out["trace"] = trace(state, "live_watch", "; ".join(notes), lane="sql", started=t)
            return out
        if declined:
            # eu_watch holds the place: answer it after all.
            out.update(status="running", summary="")
        if missing:
            out["escalate"] = "no live rows for this question (" + "; ".join(notes) + ")"
        elif mode != "live" and not any(
            e.view.endswith(("eu_watch", "gauge_levels")) for e in used
        ):
            out["escalate"] = "live data is off for this deployment"
        out["trace"] = trace(
            state,
            "live_watch",
            "; ".join(notes),
            lane="sql",
            started=t,
            evidence_ids=[e.query_id for e in used],
        )
        return out

    return live_watch


def route_after_live_watch(state: FloodState) -> str:
    if state.get("status") == "out_of_scope" and not (state.get("live_findings") or {}).get(
        "quick_query_ids"
    ):
        return "declined"
    return "escalate" if state.get("escalate") else "quick_answer"


def _claims_from(reply: dict, evs: dict[str, Evidence], prov: list[dict]) -> list[Claim]:
    claims: list[Claim] = []
    for raw in (reply.get("claims") or [])[:MAX_CLAIMS]:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        cid = f"Q{len(claims) + 1}"
        cited = [evs[q] for q in (raw.get("query_ids") or []) if isinstance(q, str) and q in evs]
        kept, dropped = cited_numbers(numbers_in(text), cited, text)
        claims.append(
            Claim(
                claim_id=cid,
                text=text,
                kind="number" if kept else "fact",
                numbers=kept,
                numbers_dropped=dropped,
                citations=[c for i, e in enumerate(cited, 1) for c in cite(cid, e, prov, i)],
            )
        )
    return claims


def make_answer(deps: Deps):
    def quick_answer(state: FloodState) -> dict:
        t = time.time()
        ids = (state.get("live_findings") or {}).get("quick_query_ids") or []
        evs = {q: Evidence(**state["evidence"][q]) for q in ids if q in state["evidence"]}
        question = str((state.get("request") or {}).get("question") or "")
        user = f"QUESTION: {question}\n\nROWS:\n{rows_block(list(evs.values()))}"
        fut = _POOL.submit(deps.llm.complete, "fast", SYSTEM, user)
        model_id = None
        try:
            text, model_id = fut.result(timeout=_timeout_s())
            claims = _claims_from(parse_json(text), evs, state.get("provenance") or [])
        except FutureTimeout:
            return _escalate_out(state, t, f"the fast lane took over {_timeout_s():.0f}s")
        except Exception as e:  # noqa: BLE001 - any model failure escalates
            return _escalate_out(state, t, f"the fast lane failed ({type(e).__name__})")
        if not claims:
            return _escalate_out(state, t, "the fast lane wrote no claim", model_id)
        summary = " ".join(c.text for c in claims)
        return {
            "claims": [c.model_dump() for c in claims],
            "summary": summary,
            "trace": trace(
                state,
                "quick_answer",
                f"{len(claims)} claims from {len(evs)} live queries",
                lane="fast",
                model_id=model_id,
                started=t,
                evidence_ids=list(evs),
            ),
        }

    return quick_answer


def _escalate_out(state: FloodState, t: float, why: str, model_id: str | None = None) -> dict:
    return {
        "escalate": why,
        "trace": trace(
            state, "quick_answer", f"no answer: {why}", lane="fast", model_id=model_id, started=t
        ),
    }


def route_after_answer(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "quick_judge"


def quick_judge(state: FloodState) -> dict:
    """The Judge's deterministic checks. A pass ends the run as answered."""
    t = time.time()
    claims = [Claim(**c) for c in state.get("claims") or []]
    evidence = {q: Evidence(**e) for q, e in (state.get("evidence") or {}).items()}
    scores, rep = judge_node.evaluate(claims, evidence, None)
    unmatched = [s.claim_id for s in scores if not s.numbers_match or not s.coverage]
    flagged = sorted(set(rep.flagged_claim_ids) | set(unmatched))
    out = {
        "judge": [s.model_dump() for s in scores],
        "judge_summary": rep.model_dump(),
        "trace": trace(
            state,
            "judge",
            f"{'PASS' if rep.passes and not flagged else 'FLAG'} overall={rep.overall:.2f} "
            f"hallucination={rep.hallucination_rate:.0%} coverage={rep.citation_coverage:.0%} "
            f"numbers={rep.numeric_accuracy:.0%} flagged={flagged or '-'}",
            lane="none",
            model_id=rep.model_id,
            started=t,
        ),
    }
    if not rep.passes or flagged:
        out["escalate"] = f"judge flagged {', '.join(flagged) or 'the answer'}"
    else:
        out["status"] = "answered"
    return out


def route_after_quick_judge(state: FloodState) -> str:
    return "escalate" if state.get("escalate") else "done"


def escalate(state: FloodState) -> dict:
    """Hand the run to the full lane and say why on the trace."""
    why = state.get("escalate") or "quick lane could not answer"
    reason = f"{state.get('router_reason') or 'chose quick'}; escalated: {why}"
    return {
        "lane": FULL,
        "router_reason": reason,
        "escalate": None,
        "claims": [],
        "judge": [],
        "judge_summary": {},
        "summary": "",
        "status": "running",
        "trace": trace(state, "router", f"escalated: {why}; running the full lane", lane="none"),
    }
