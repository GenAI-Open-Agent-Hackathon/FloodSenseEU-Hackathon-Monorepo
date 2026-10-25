"""Independent Zetaris queries fan out and come back in call order.

The parallel helper must match a sequential FakeZetaris read: same view,
SQL, row count, and sample. Watchers, Investigator, and Exposure keep that
order in the evidence record so claim text does not depend on which
query finished first.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from floodsense_agents.events import EVENTS  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes.exposure import make as make_exposure  # noqa: E402
from floodsense_agents.nodes.investigator import make as make_investigator  # noqa: E402
from floodsense_agents.nodes.watchers import make as make_watchers  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris, run_sql_parallel  # noqa: E402

_JOBS = [
    (
        "SELECT point_id, ts_utc, discharge_m3s FROM floodsense_seed.hazard_timeline "
        "WHERE ts_utc BETWEEN ? AND ? AND discharge_m3s IS NOT NULL ORDER BY ts_utc",
        ("2024-10-29T00:00:00Z", "2024-10-29T18:00:00Z"),
    ),
    (
        "SELECT dataset, publisher, licence FROM floodsense_seed.provenance ORDER BY dataset",
        None,
    ),
    (
        "SELECT COUNT(*) AS policies, SUM(sum_insured_eur) AS sum_insured_eur "
        "FROM floodsense_seed.exposure_join WHERE in_footprint = 1",
        None,
    ),
]


class _Slow(FakeZetaris):
    def __init__(self) -> None:
        super().__init__()
        self._gate = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0

    def run_sql(self, sql: str, params=None):
        with self._gate:
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            time.sleep(0.2)
            return super().run_sql(sql, params)
        finally:
            with self._gate:
                self.inflight -= 1


def _deps(zetaris: FakeZetaris | None = None) -> Deps:
    return Deps(zetaris=zetaris or FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())


def _event_state() -> dict:
    return {
        "run_id": "parallel",
        "event_id": "EMSR773",
        "event": EVENTS["EMSR773"].as_dict(),
        "request": {"question": "Why are our Valencia sites at risk?", "lang": "en"},
        "provenance": [],
        "evidence": {},
        "anomalies": [],
        "trace": [],
        "hypotheses": [],
        "claims": [],
        "revise_rounds": 0,
        "model_ids": [],
    }


class ParallelSqlTest(unittest.TestCase):
    def test_parallel_rows_match_sequential_fake_zetaris(self) -> None:
        left = FakeZetaris()
        right = FakeZetaris()
        sequential = [left.run_sql(sql, params) for sql, params in _JOBS]
        parallel = run_sql_parallel(right, _JOBS)
        self.assertEqual(len(parallel), len(sequential))
        for seq, par in zip(sequential, parallel):
            self.assertEqual(par.view, seq.view)
            self.assertEqual(par.sql, seq.sql)
            self.assertEqual(par.row_count, seq.row_count)
            self.assertEqual(par.rows_sample, seq.rows_sample)
            self.assertIsNone(par.error)

    def test_parallel_rows_match_when_a_loop_is_already_running(self) -> None:
        left = FakeZetaris()
        sequential = [left.run_sql(sql, params) for sql, params in _JOBS]

        async def _inside():
            return run_sql_parallel(FakeZetaris(), _JOBS)

        parallel = asyncio.run(_inside())
        self.assertEqual(len(parallel), len(sequential))
        for seq, par in zip(sequential, parallel):
            self.assertEqual(par.view, seq.view)
            self.assertEqual(par.sql, seq.sql)
            self.assertEqual(par.row_count, seq.row_count)
            self.assertEqual(par.rows_sample, seq.rows_sample)
            self.assertIsNone(par.error)

    def test_independent_queries_overlap(self) -> None:
        slow = _Slow()
        run_sql_parallel(slow, _JOBS)
        self.assertGreater(slow.max_inflight, 1)

    def test_watchers_keep_hazard_then_provenance_order(self) -> None:
        out = make_watchers(_deps())(_event_state())
        sqls = [row["sql"] for row in out["evidence"].values()]
        self.assertEqual(len(sqls), 4)
        self.assertIn("rain_mm", sqls[0])
        self.assertIn("discharge_m3s", sqls[1])
        self.assertIn("warning_level", sqls[2])
        self.assertIn("provenance", sqls[3])
        kinds = [item["kind"] for item in out["anomalies"]]
        self.assertLess(kinds.index("rain"), kinds.index("discharge"))
        self.assertLess(kinds.index("discharge"), kinds.index("warning"))
        replay = FakeZetaris()
        for row in out["evidence"].values():
            again = replay.run_sql(row["sql"])
            self.assertEqual(again.rows_sample, row["rows_sample"])
            self.assertEqual(again.row_count, row["row_count"])
            self.assertEqual(again.view, row["view"])

    def test_investigator_keeps_claim_text_and_evidence_order(self) -> None:
        first = make_investigator(_deps())(_event_state())
        second = make_investigator(_deps())(_event_state())
        self.assertEqual(
            [c["text"] for c in first["claims"]],
            [c["text"] for c in second["claims"]],
        )
        self.assertEqual(
            [h["link"] for h in first["hypotheses"]],
            ["rain->catchment", "catchment->river", "river->site"],
        )
        views = [row["view"].split(".")[-1] for row in first["evidence"].values()]
        self.assertEqual(
            views,
            [
                "hazard_timeline",
                "hazard_timeline",
                "discharge_daily",
                "exposure_join",
                "hazard_timeline",
            ],
        )

    def test_exposure_keeps_sample_segment_and_total_order(self) -> None:
        out = make_exposure(_deps())(_event_state())
        sqls = [row["sql"] for row in out["evidence"].values()]
        self.assertEqual(len(sqls), 3)
        self.assertIn("ORDER BY sum_insured_eur DESC", sqls[0])
        self.assertNotIn("GROUP BY", sqls[0])
        self.assertIn("GROUP BY segment", sqls[1])
        self.assertIn("COUNT(*)", sqls[2])
        self.assertNotIn("GROUP BY", sqls[2])
        self.assertEqual(out["exposure"]["policies"], 7)
        self.assertEqual(out["exposure"]["sum_insured_eur"], 21_600_000)
        self.assertEqual(
            [c["text"] for c in out["claims"]],
            [c["text"] for c in make_exposure(_deps())(_event_state())["claims"]],
        )


if __name__ == "__main__":
    unittest.main()
