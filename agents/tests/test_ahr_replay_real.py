"""The Ahr 2021 replay on the real Open-Meteo extract, with FF_LIVE_DATA on.

A live run scored Judge 0.40: every hazard query read floodsense.* (Valencia
only), the Skeptic counted Valencia's footprint sites as the Ahr's, the hourly
rain line (30 mm/h) never fires on ERA5's smoothed 5.6-18.5 mm/h, and the
model copied the bbox literals into a claim's numbers. The fake here holds the
Ahr rows only in floodsense_seed, parsed from migrations 051/052 (the real
GloFAS / ERA5 values), and none in floodsense.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from floodsense_agents.events import EVENTS, hazard_schema  # noqa: E402
from floodsense_agents.graph import build_graph  # noqa: E402
from floodsense_agents.models import Evidence, RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes.investigator import cited_numbers  # noqa: E402
from floodsense_agents.nodes.memory import _same_event  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402

MIGRATIONS = Path(__file__).resolve().parents[2] / "zetaris" / "migrations"
_HOURLY = re.compile(r"\('(AHR0\d)', '(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', ([\d.]+)D, ([\d.]+)D\)")
_DAILY = re.compile(r"\('(AHR0\d)', '(\d{4}-\d{2}-\d{2})', ([\d.]+)D, '([^']+)'\)")


def real_ahr() -> FakeZetaris:
    """FakeZetaris whose Ahr rows are the real 051/052 extract, in floodsense_seed only."""
    z = FakeZetaris()
    for schema in ("floodsense_seed", "floodsense"):
        for view in ("hazard_timeline", "discharge_daily", "hazard_now"):
            z._conn.execute(f"DELETE FROM {schema}.{view} WHERE point_id LIKE 'AHR%'")
    hourly = _HOURLY.findall((MIGRATIONS / "052_seed_hazard_timeline_ahr.sql").read_text("utf-8"))
    daily = _DAILY.findall((MIGRATIONS / "051_seed_discharge_daily_ahr.sql").read_text("utf-8"))
    assert len(hourly) == 384 and len(daily) == 44, (len(hourly), len(daily))
    z._conn.executemany(
        "INSERT INTO floodsense_seed.hazard_timeline VALUES (?,?,?,?,NULL)",
        [(p, f"{d}T{t}Z", float(r), float(q)) for p, d, t, r, q in hourly],
    )
    z._conn.executemany(
        "INSERT INTO floodsense_seed.discharge_daily VALUES (?,?,?,?)",
        [(p, d, float(q), s) for p, d, q, s in daily],
    )
    z._conn.commit()
    return z


def run_replay(z: FakeZetaris) -> dict:
    deps = Deps(zetaris=z, llm=FakeNightshift(), memory=NoMemory())
    rt = Runtime(graph=build_graph(deps), deps=deps)
    with mock.patch.object(settings, "live_data", True):
        return rt.start(
            RunRequest(
                question="Why was Altenahr at risk on 14 Jul 2021?",
                event_id="EMSR517",
                context={
                    "page": "replay",
                    "role": "insurer",
                    "event_id": "EMSR517",
                    "replay_date": "2021-07-14",
                },
            )
        )


class AhrReplayOnRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.out = run_replay(real_ahr())

    def _hazard(self) -> list[dict]:
        return [
            e
            for e in self.out["evidence"].values()
            if re.search(r"\b(hazard_timeline|discharge_daily)\b", e.get("sql") or "")
        ]

    def test_hazard_schema_is_seed_for_the_ahr_and_configured_for_valencia(self) -> None:
        self.assertEqual(hazard_schema(EVENTS["EMSR517"].as_dict(), "floodsense"), "floodsense_seed")
        self.assertEqual(hazard_schema({"event_id": "EMSR517"}, "floodsense"), "floodsense_seed")
        self.assertEqual(hazard_schema(EVENTS["EMSR773"].as_dict(), "floodsense"), "floodsense")

    def test_every_hazard_query_reads_floodsense_seed(self) -> None:
        hazard = self._hazard()
        self.assertTrue(hazard)
        for e in hazard:
            self.assertIn("floodsense_seed.", e["sql"])
            self.assertNotRegex(e["sql"], r"(?<!_)\bfloodsense\.(hazard_timeline|discharge_daily)")

    def test_watchers_flag_the_real_discharge_and_rain_total(self) -> None:
        kinds = {(a["kind"], a.get("unit")) for a in self.out["anomalies"]}
        self.assertIn(("discharge", "m3/s"), kinds)
        self.assertIn(("rain", "mm"), kinds, "the window total catches ERA5's smoothed storm")
        peak = max(a["value"] for a in self.out["anomalies"] if a["kind"] == "discharge")
        self.assertLess(peak, 300, "GloFAS reanalysis, not the ~1000 m3/s literature figure")

    def test_rain_and_river_hypotheses_survive_the_skeptic(self) -> None:
        status = {h["link"]: h["status"] for h in self.out["hypotheses"]}
        self.assertEqual(status.get("rain->catchment"), "supported", self.out["hypotheses"])
        self.assertEqual(status.get("catchment->river"), "supported", self.out["hypotheses"])

    def test_footprint_check_is_inside_the_ahr_bbox(self) -> None:
        site = [h for h in self.out["hypotheses"] if h["link"] == "river->site"]
        for h in site:
            for q in h.get("evidence") or []:
                sql = self.out["evidence"][q]["sql"]
                if "exposure_join" in sql:
                    self.assertIn("lat BETWEEN 50.2 AND 50.7", sql)

    def test_number_claims_match_their_rows(self) -> None:
        scores = {s["claim_id"]: s for s in self.out["judge"]}
        numbered = [c for c in self.out["claims"] if c["numbers"] and c["claim_id"] in scores]
        self.assertTrue(numbered)
        for c in numbered:
            self.assertTrue(scores[c["claim_id"]]["numbers_match"], (c, scores[c["claim_id"]]))


class EmptyCitationClaims(unittest.TestCase):
    def test_a_model_claim_citing_only_an_empty_query_is_dropped(self) -> None:
        import json

        def investigator(system, user):
            blocks = re.findall(r"query_id=(\S+) view=(\S+) .*?rows=(\d+)", user)
            empty = next(q for q, v, n in blocks if int(n) == 0)
            full = next(q for q, v, n in blocks if v.endswith("discharge_daily") and int(n) > 0)
            return json.dumps(
                {
                    "hypotheses": [
                        {"id": "H2", "link": "catchment->river", "statement": "River rose",
                         "claim_ids": ["C1", "C2"]}
                    ],
                    "claims": [
                        {"claim_id": "C1", "text": "Daily discharge at Altenahr reached 249.61 m3/s.",
                         "kind": "number", "numbers": [249.61], "query_ids": [full], "hypothesis_id": "H2"},
                        {"claim_id": "C2", "text": "No warning level was recorded.", "kind": "fact",
                         "numbers": [], "query_ids": [empty], "hypothesis_id": "H2"},
                    ],
                    "summary": "River rose [C1].",
                }
            )

        deps = Deps(zetaris=real_ahr(), llm=FakeNightshift({"investigator": investigator}), memory=NoMemory())
        rt = Runtime(graph=build_graph(deps), deps=deps)
        with mock.patch.object(settings, "live_data", True):
            out = rt.start(RunRequest(question="Why was Altenahr at risk on 14 Jul 2021?", event_id="EMSR517"))
        ids = {c["claim_id"] for c in out["claims"]}
        self.assertIn("C1", ids)
        self.assertNotIn("C2", ids)


class NumbersAndMemory(unittest.TestCase):
    def test_sql_literals_leave_the_numbers_list(self) -> None:
        e = Evidence(
            query_id="q",
            view="floodsense.exposure_join",
            sql="SELECT COUNT(*) AS n FROM floodsense.exposure_join WHERE in_footprint = TRUE "
            "AND lat BETWEEN 50.2 AND 50.7 AND lon BETWEEN 6.6 AND 7.4",
            rows_sample=[{"n": 0}],
            row_count=1,
            executed_at_utc="2026-10-27T00:00:00Z",
        )
        self.assertEqual(cited_numbers([0.0, 50.2, 50.7, 6.6, 7.4], [e]), [0.0])
        # A wrong number that is not a literal stays, so the Judge flags it.
        self.assertEqual(cited_numbers([999.0], [e]), [999.0])
        # Day and year of a spelled-out date are not values (live run: C3 [13, 2021]).
        text = "Rain at all four points started on 13 Jul 2021 at 00:00 UTC."
        self.assertEqual(cited_numbers([13.0, 2021.0], [e], text), [])

    def test_memory_from_another_event_is_not_recalled(self) -> None:
        mems = [
            {"memory_id": "v", "tags": ["event:EMSR773"]},
            {"memory_id": "a", "tags": ["event:EMSR517"]},
            {"memory_id": "u", "tags": []},
        ]
        self.assertEqual([m["memory_id"] for m in _same_event(mems, "EMSR517")], ["a", "u"])


if __name__ == "__main__":
    unittest.main()
