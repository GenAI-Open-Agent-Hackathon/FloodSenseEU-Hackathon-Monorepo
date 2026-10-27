"""Benchmark one full FloodSense run against the real Nightshift and Zetaris.

Runs the graph in-process up to the HITL interrupt and prints, per node, the
trace latency and, per model call, the lane, task, seconds and answering
model. Reads configuration from the process environment only; it never
prints a secret. Meant to run where the agents' env is already set, for
example inside the agents container without rebuilding it:

    docker cp agents/floodsense_agents <ctr>:/tmp/bench/floodsense_agents
    docker cp scripts/bench_nightshift.py <ctr>:/tmp/bench/
    docker exec -w /tmp/bench -e PYTHONPATH=/tmp/bench -e CHECKPOINTER=memory \
        <ctr> python bench_nightshift.py [--event EMSR773] [--question "..."]

PYTHONPATH decides which agents code is measured (/app = the image's,
/tmp/bench = a worktree copy), so before/after run on the same machine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid

os.environ.setdefault("CHECKPOINTER", "memory")

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from floodsense_agents import labelling  # noqa: E402
from floodsense_agents.events import spec  # noqa: E402
from floodsense_agents.graph import build_deps, build_graph  # noqa: E402


class TimedLLM:
    """Wraps deps.llm; records one row per call. Thread-safe."""

    def __init__(self, inner) -> None:
        self.inner, self.rows, self.lock = inner, [], threading.Lock()

    def complete(self, lane, system, user, *, json=True):
        task = system.split("\n", 1)[0].replace("TASK:", "").strip()
        t = time.time()
        err, model = None, None
        try:
            text, model = self.inner.complete(lane, system, user, json=json)
            return text, model
        except Exception as e:
            err = type(e).__name__ + ": " + str(e)[:80]
            raise
        finally:
            with self.lock:
                self.rows.append(
                    {
                        "task": task,
                        "lane": lane,
                        "s": round(time.time() - t, 1),
                        "start": round(t - T0, 1),
                        "prompt_chars": len(system) + len(user),
                        "model": model,
                        "error": err,
                    }
                )


T0 = time.time()


def main() -> int:
    global T0
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", default="EMSR773")
    ap.add_argument("--question", default="Why are our Valencia sites at risk?")
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    a = ap.parse_args()

    deps = build_deps()
    timed = TimedLLM(deps.llm)
    deps.llm = timed
    graph = build_graph(deps, MemorySaver())
    rid = f"bench-{uuid.uuid4().hex[:8]}"
    ev = spec(a.event)
    req = {
        "question": a.question,
        "event_id": ev.event_id,
        "customer_id": "demo-insurer",
        "replay_ts": None,
        "lang": "en",
        "reviewer": None,
    }
    served_from, cached_at = labelling.computation_label(None, live=False)
    T0 = time.time()
    out = graph.invoke(
        {
            "run_id": rid,
            "thread_id": rid,
            "event_id": ev.event_id,
            "customer_id": "demo-insurer",
            "replay_ts": None,
            "request": req,
            "event": ev.as_dict(),
            "served_from": served_from,
            "cached_at": cached_at,
            "trace": [],
            "revise_rounds": 0,
            "repair_rounds": 0,
            "model_ids": [],
        },
        {"configurable": {"thread_id": rid}},
    )
    total = time.time() - T0
    nodes = [
        {"node": t["node"], "s": round((t.get("latency_ms") or 0) / 1000, 1), "lane": t.get("lane")}
        for t in out.get("trace", [])
    ]
    summary = out.get("judge_summary") or {}
    result = {
        "total_s": round(total, 1),
        "nodes": nodes,
        "calls": timed.rows,
        "judge": {
            k: summary.get(k) for k in ("overall", "passes", "n_claims", "flagged_claim_ids")
        },
        "repair_rounds": out.get("repair_rounds"),
        "revise_rounds": out.get("revise_rounds"),
    }
    if a.json:
        print(json.dumps(result))
        return 0
    print(f"total {result['total_s']} s  judge={result['judge']}  repair={result['repair_rounds']}")
    for n in nodes:
        print(f"  node {n['node']:<14} {n['s']:>7.1f} s  lane={n['lane']}")
    for c in timed.rows:
        print(
            f"  call {c['task']:<13} {c['lane']:<5} start={c['start']:>6.1f} {c['s']:>6.1f} s "
            f"chars={c['prompt_chars']:>6} model={c['model']} {c['error'] or ''}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
