"""Evaluation runner.

The headline number is the hallucination rate: the share of claims their own
citations do not support, as scored by the Judge. Also reports citation
coverage, numeric accuracy, Judge pass rate, Skeptic rejections, and which
expected and forbidden tokens were found.

    python evals/run_evals.py                          # both events, current env (fakes when no credentials)
    python evals/run_evals.py --event EMSR773 --strict --out reports/evals.md

Targets (proposal): hallucination <= 5 %, citation coverage 100 %, numeric
accuracy 100 %.
--strict exits 1 when a target is missed, for CI.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("FF_JUDGE", "true")

import yaml  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from floodsense_agents.graph import build_deps, build_graph  # noqa: E402
from floodsense_agents.models import ApprovalDecision, RunRequest  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402

HERE = Path(__file__).resolve().parent
EVENTS = {"EMSR773": "valencia_2024.yaml", "EMSR517": "ahr_2021.yaml"}
TARGETS = {
    "hallucination_rate": ("<=", 0.05),
    "citation_coverage": (">=", 1.0),
    "numeric_accuracy": (">=", 1.0),
}


def mentions(text: str, token: str) -> bool:
    return re.search(rf"(?<![\w.,]){re.escape(token.lower())}(?![\w])", text.lower()) is not None


def run_item(rt: Runtime, spec: dict, item: dict, provider: str | None = None) -> dict:
    t0 = time.time()
    req = RunRequest(
        question=item["question"],
        event_id=spec["event_id"],
        customer_id=spec.get("customer_id", "demo-insurer"),
        replay_ts=item.get("replay_ts"),
        # layer (c): an item that needs a document names the search text; others leave it unset.
        **({"doc_query": item["doc_query"]} if item.get("doc_query") else {}),
        # None keeps the deployment default (Nightshift); a test provider needs LLM_PROVIDER_SWITCH.
        **({"llm_provider": provider} if provider else {}),
    )
    s = rt.start(req)
    # An item may declare that the right answer is no answer. Scoring a
    # refusal against expect/forbid tokens would punish the gate for working.
    if item.get("expect_declined"):
        declined = s["status"] == "out_of_scope"
        return {
            "id": item["id"],
            "question": item["question"],
            "declined": declined,
            "expected_declined": True,
            "ok": declined,
            "reason": (s.get("scope") or {}).get("reason", ""),
            "summary": s.get("summary", ""),
            # Neutral values: a refusal has no answer to score, and averaging
            # it in would flatter or punish the quality numbers either way.
            "hallucination_rate": 0.0,
            "citation_coverage": 1.0,
            "numeric_accuracy": 1.0,
            "judge_passes": True,
            "judge_overall": 0.0,
            "n_claims": 0,
            "status": "out_of_scope" if declined else s["status"],
            "expect_hits": "0/0",
            "expect_hit_rate": None,
            "forbid_violations": [
                f for f in item.get("forbid", []) if mentions(s.get("summary") or "", f)
            ],
            "repair_rounds": 0,
            "skeptic_rejections": 0,
            "model_ids": [],
            "elapsed_s": round(time.time() - t0, 2),
        }
    if s["status"] == "awaiting_approval":
        s = rt.resume(s["run_id"], ApprovalDecision(action="approve", reviewer="evals"))
    text = " ".join(
        [s.get("summary") or ""]
        + [c["text"] for c in s["claims"]]
        + [a["text"] for a in s["playbook"]]
    )
    js = s.get("judge_summary") or {}
    expect, forbid = item.get("expect", []), item.get("forbid", [])
    hits = [e for e in expect if mentions(text, e)]
    viol = [f for f in forbid if mentions(text, f)]
    # expect_source: the corpus URL a cited claim should carry (layer (c) items only).
    source = item.get("expect_source")
    cited = {c.get("source_url") for cl in s["claims"] for c in (cl.get("citations") or [])}
    return {
        "expect_source": source,
        "source_cited": (source in cited) if source else None,
        "id": item["id"],
        "question": item["question"],
        "status": s["status"],
        "elapsed_s": round(time.time() - t0, 2),
        "n_claims": js.get("n_claims", 0),
        "hallucination_rate": js.get("hallucination_rate", 1.0),
        "citation_coverage": js.get("citation_coverage", 0.0),
        "numeric_accuracy": js.get("numeric_accuracy", 0.0),
        "judge_passes": js.get("passes", False),
        "judge_overall": js.get("overall", 0.0),
        "repair_rounds": s.get("repair_rounds", 0),
        "revise_rounds": s.get("revise_rounds", 0),
        "skeptic_rejections": sum(1 for h in s["hypotheses"] if h["status"] == "not_supported"),
        "expect_hits": f"{len(hits)}/{len(expect)}",
        "expect_hit_rate": (len(hits) / len(expect)) if expect else None,
        "forbid_violations": viol,
        "model_ids": sorted(set(s.get("model_ids", []))),
        "summary": s.get("summary", ""),
    }


def aggregate(rows: list[dict]) -> dict:
    # A refused question has no answer, so it is counted as a refusal and kept
    # out of the answer-quality means.
    refusals = [r for r in rows if r.get("expected_declined")]
    answered = [r for r in rows if not r.get("expected_declined")] or rows
    n = len(answered) or 1
    rated = [r["expect_hit_rate"] for r in answered if r["expect_hit_rate"] is not None]
    rows = answered
    return {
        "items": len(rows),
        "refusals_expected": len(refusals),
        "refusals_correct": sum(1 for r in refusals if r["declined"]),
        "hallucination_rate": round(sum(r["hallucination_rate"] for r in rows) / n, 4),
        "citation_coverage": round(sum(r["citation_coverage"] for r in rows) / n, 4),
        "numeric_accuracy": round(sum(r["numeric_accuracy"] for r in rows) / n, 4),
        "judge_pass_rate": round(sum(r["judge_passes"] for r in rows) / n, 4),
        "judge_overall": round(sum(r["judge_overall"] for r in rows) / n, 3),
        "expect_hit_rate": round(sum(rated) / len(rated), 4) if rated else None,
        "forbid_violations": sum(len(r["forbid_violations"]) for r in rows),
        "repair_rounds": sum(r["repair_rounds"] for r in rows),
        "skeptic_rejections": sum(r["skeptic_rejections"] for r in rows),
        "mean_elapsed_s": round(sum(r["elapsed_s"] for r in rows) / n, 2),
    }


def ok(a: dict) -> dict[str, bool]:
    return {k: (a[k] <= v if op == "<=" else a[k] >= v) for k, (op, v) in TARGETS.items()}


def markdown(results: dict) -> str:
    out = [
        f"# FloodSense evals — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        f"LLM `{results['llm']}` (provider `{results.get('provider', 'default')}`) · Zetaris `{results['zetaris']}` · targets: hallucination ≤ 5 %, "
        f"coverage 100 %, numeric 100 %",
        "",
    ]
    for ev, block in results["events"].items():
        a, flags = block["aggregate"], ok(block["aggregate"])
        mark = lambda k: "✅" if flags[k] else "❌"  # noqa: E731
        rate = a["expect_hit_rate"]
        expect = rate if rate is None else format(rate, ".0%")
        out += [
            f"## {ev}",
            "",
            f"**hallucination {a['hallucination_rate']:.1%}** {mark('hallucination_rate')} · "
            f"**coverage {a['citation_coverage']:.0%}** {mark('citation_coverage')} · "
            f"**numeric {a['numeric_accuracy']:.0%}** {mark('numeric_accuracy')} · judge pass "
            f"{a['judge_pass_rate']:.0%} (overall {a['judge_overall']:.2f}) · "
            f"expected tokens {expect} · "
            f"forbidden figures {a['forbid_violations']} · "
            f"repairs {a['repair_rounds']} · skeptic rejections {a['skeptic_rejections']} · "
            f"{a['mean_elapsed_s']} s/item",
            "",
            "| id | halluc. | coverage | numeric | claims | repairs | expected | forbidden | "
            "status |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in block["rows"]:
            out.append(
                f"| {r['id']} | {r['hallucination_rate']:.0%} | {r['citation_coverage']:.0%} | "
                f"{r['numeric_accuracy']:.0%} | {r['n_claims']} | {r['repair_rounds']} | "
                f"{r['expect_hits']} | {', '.join(r['forbid_violations']) or '—'} | {r['status']} |"
            )
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", choices=list(EVENTS), action="append")
    ap.add_argument("--out", help="markdown report path (a .json twin is written beside it)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a target is missed")
    ap.add_argument(
        "--provider", help="llm_provider for every run (default: the deployment default)"
    )
    ap.add_argument("--items", help="comma-separated item ids to run (default: all)")
    args = ap.parse_args(argv)
    deps = build_deps()
    rt = Runtime(graph=build_graph(deps, MemorySaver(), ff_judge=True), deps=deps)
    results = {
        "llm": type(deps.llm).__name__,
        "provider": args.provider or "default",
        "zetaris": type(deps.zetaris).__name__,
        "events": {},
    }
    wanted = {i.strip() for i in args.items.split(",")} if args.items else None
    if args.provider:
        # Fail once, before any run, rather than with a traceback at the first item.
        RunRequest(question="provider check", llm_provider=args.provider)
    if wanted:
        known = {
            item["id"]
            for ev in args.event or list(EVENTS)
            for item in yaml.safe_load((HERE / EVENTS[ev]).read_text(encoding="utf-8"))["items"]
        }
        unknown = sorted(wanted - known)
        if unknown:
            print(f"error: unknown eval item id(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
    for ev in args.event or list(EVENTS):
        spec = yaml.safe_load((HERE / EVENTS[ev]).read_text(encoding="utf-8"))
        items = [i for i in spec["items"] if wanted is None or i["id"] in wanted]
        if not items:
            continue
        rows = [run_item(rt, spec, item, args.provider) for item in items]
        for row in rows:
            row["provider"] = args.provider or "default"
        results["events"][ev] = {"rows": rows, "aggregate": aggregate(rows)}
        a = results["events"][ev]["aggregate"]
        print(
            f"{ev}: hallucination={a['hallucination_rate']:.1%} "
            f"coverage={a['citation_coverage']:.0%} numeric={a['numeric_accuracy']:.0%} "
            f"judge_pass={a['judge_pass_rate']:.0%} expect_hit={a['expect_hit_rate']} "
            f"forbid={a['forbid_violations']} repairs={a['repair_rounds']}"
        )
    md = markdown(results)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(md, encoding="utf-8")
        Path(args.out).with_suffix(".json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"report: {args.out}")
    missed = any(not all(ok(b["aggregate"]).values()) for b in results["events"].values())
    return 1 if (args.strict and missed) else 0


if __name__ == "__main__":
    sys.exit(main())
