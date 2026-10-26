"""GET /views/{name}: allowlist, schema from FF_LIVE_DATA, typed rows."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from fastapi.testclient import TestClient  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from floodsense_agents import __main__ as service  # noqa: E402
from floodsense_agents.graph import build_graph  # noqa: E402
from floodsense_agents.models import Evidence  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402


class StringZetaris:
    """Answers like the REST API: every value a string."""

    def __init__(self) -> None:
        self.sql: list[str] = []

    def run_sql(self, sql, params=None, sample=20):
        self.sql.append(sql)
        self.sample = sample
        rows = [
            {"policy_id": "P-1", "site_id": "S-1", "lat": "39.4", "lon": "-0.4",
             "in_footprint": "true", "sum_insured_eur": "1000000", "segment": "retail",
             "synthetic": "yes"},
            {"policy_id": "P-2", "site_id": "S-2", "lat": "39.5", "lon": "-0.3",
             "in_footprint": "false", "sum_insured_eur": "", "segment": "office",
             "synthetic": "yes"},
        ]
        return Evidence(query_id="q-1", view="x", sql=sql, rows_sample=rows[:sample],
                        row_count=2, executed_at_utc="2026-10-26T00:00:00Z")


class ViewsTest(unittest.TestCase):
    def _client(self, zetaris) -> TestClient:
        deps = Deps(zetaris=zetaris, llm=FakeNightshift(), memory=NoMemory())
        service.set_runtime(Runtime(graph=build_graph(deps, MemorySaver(), ff_judge=True), deps=deps))
        return TestClient(service.app)

    def test_unknown_view_is_404_and_never_queried(self) -> None:
        z = StringZetaris()
        c = self._client(z)
        for name in ("policies", "exposure_join;drop", "floodsense.provenance", "pg_tables"):
            self.assertEqual(c.get(f"/views/{name}").status_code, 404, name)
        self.assertEqual(z.sql, [])

    def test_discharge_daily_is_a_bare_array_past_the_sample_cap(self) -> None:
        c = self._client(FakeZetaris())
        r = c.get("/views/discharge_daily")
        self.assertEqual(r.status_code, 200)
        rows = r.json()
        self.assertIsInstance(rows, list)
        fake = service.runtime().deps.zetaris
        everything = fake.run_sql(f"SELECT * FROM {settings.schema}.discharge_daily", sample=10_000)
        self.assertEqual(len(rows), everything.row_count)
        self.assertIsInstance(rows[0]["discharge_m3s"], float)
        self.assertEqual(r.headers["x-schema"], settings.schema)
        self.assertTrue(r.headers["x-query-id"])

    def test_strings_become_numbers_and_booleans(self) -> None:
        z = StringZetaris()
        rows = self._client(z).get("/views/exposure_join").json()
        self.assertEqual(rows[0]["lat"], 39.4)
        self.assertIs(rows[0]["in_footprint"], True)
        self.assertIs(rows[1]["in_footprint"], False)
        self.assertIsNone(rows[1]["sum_insured_eur"])
        self.assertEqual(rows[0]["segment"], "retail")
        self.assertIn("LIMIT 5000", z.sql[0])
        self.assertEqual(z.sample, 5000)  # Evidence keeps every row, not the 20-row sample

    def test_schema_follows_ff_live_data(self) -> None:
        z = StringZetaris()
        c = self._client(z)
        with mock.patch.object(settings, "live_data", True):
            c.get("/views/exposure_join")
        with mock.patch.object(settings, "live_data", False):
            c.get("/views/exposure_join")
        self.assertIn("FROM floodsense.exposure_join", z.sql[0])
        self.assertIn("FROM floodsense_seed.exposure_join", z.sql[1])

    def test_event_id_is_ignored_on_views_without_the_column(self) -> None:
        z = StringZetaris()
        self._client(z).get("/views/exposure_join", params={"event_id": "x' OR 1=1"})
        self.assertNotIn("WHERE", z.sql[0])

    def test_a_failed_read_is_502(self) -> None:
        # The fake has no hazard_now table, so the read errors.
        self.assertEqual(self._client(FakeZetaris()).get("/views/hazard_now").status_code, 502)


if __name__ == "__main__":
    unittest.main()
