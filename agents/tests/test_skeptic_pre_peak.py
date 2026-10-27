"""A replay before the discharge peak still keeps the rain link (Ahr, 15:00 UTC)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from floodsense_agents.graph import build_graph  # noqa: E402
from floodsense_agents.models import RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402


class PrePeakReplay(unittest.TestCase):
    def test_rain_survives_and_only_the_river_link_drops(self) -> None:
        deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
        out = Runtime(graph=build_graph(deps), deps=deps).start(
            RunRequest(
                question="What was known by 15:00 UTC on 14 July 2021?",
                event_id="EMSR517",
                replay_ts="2021-07-14T15:00:00Z",
            )
        )
        links = {h["link"]: h for h in out["hypotheses"]}
        self.assertEqual(links["rain->catchment"]["status"], "supported")
        self.assertNotIn("catchment->river", links)
        self.assertIn("rain", out["summary"].lower())
        self.assertFalse(any("1000" in c["text"] for c in out["claims"]))
        sqls = [e["sql"] for e in out["evidence"].values() if "first_rain" in e["sql"]]
        self.assertTrue(sqls)
        self.assertTrue(all("hazard_timeline r," not in sql for sql in sqls), "no cross join")


if __name__ == "__main__":
    unittest.main()
