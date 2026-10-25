"""Watchers can read gauge_levels. Live data stays off by default."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from floodsense_agents.events import EVENTS  # noqa: E402
from floodsense_agents.governance import CONTRACT_VIEWS, OWNERS  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes.watchers import make as make_watchers  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _state() -> dict:
    return {
        "run_id": "gauges",
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


class GaugeContractTest(unittest.TestCase):
    def test_the_gauge_view_is_owned_and_live_stays_off(self) -> None:
        self.assertIn("gauge_levels", CONTRACT_VIEWS)
        self.assertIn("gauge_levels", OWNERS)
        self.assertEqual(OWNERS["gauge_levels"].view, "gauge_levels")
        settings = (ROOT / "agents" / "floodsense_agents" / "settings.py").read_text(encoding="utf-8")
        example = (ROOT / "agents" / ".env.example").read_text(encoding="utf-8")
        self.assertIn('_flag("FF_LIVE_DATA", False)', settings)
        self.assertIn("FF_LIVE_DATA=false", example)

    def test_watchers_read_gauge_levels_for_the_event_window(self) -> None:
        deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
        out = make_watchers(deps)(_state())
        sqls = [row["sql"] for row in out["evidence"].values()]
        self.assertEqual(len(sqls), 5)
        gauge_sql = next(sql for sql in sqls if "gauge_levels" in sql)
        self.assertIn("level_cm", gauge_sql)
        self.assertNotIn("SELECT *", gauge_sql.upper())
        again = FakeZetaris().run_sql(gauge_sql)
        self.assertIsNone(again.error)
        self.assertEqual(again.row_count, 3)
        self.assertEqual({row["station"] for row in again.rows_sample}, {"BONN", "KÖLN", "KOBLENZ"})
        self.assertTrue(all(row["level_cm"] is None for row in again.rows_sample))
        self.assertTrue(all(row["source"] == "seed:pegelonline" for row in again.rows_sample))
        self.assertEqual({row["water"] for row in again.rows_sample}, {"RHEIN"})
        kinds = {item["kind"] for item in out["anomalies"]}
        self.assertNotIn("gauge", kinds)
        documented = {row["dataset"] for row in out["provenance"]}
        self.assertIn("gauge_levels", documented)


if __name__ == "__main__":
    unittest.main()
