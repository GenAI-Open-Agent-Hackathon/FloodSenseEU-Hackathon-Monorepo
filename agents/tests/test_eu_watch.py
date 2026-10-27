"""Europe live watch: place routing, live mode, and the eu_watch / gauge_levels answer."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from floodsense_agents.events import route_event  # noqa: E402
from floodsense_agents.governance import CONTRACT_VIEWS, OWNERS  # noqa: E402
from floodsense_agents.live import classify  # noqa: E402
from floodsense_agents.models import RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes import scope  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.watch import (  # noqa: E402
    EU_POINT_IDS,
    STATIONS,
    is_watch_only,
    watch_target,
)
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BUDAPEST = "Is the Danube at Budapest at risk right now?"
DRESDEN = "What about the Elbe in Dresden?"


def _poller():
    path = ROOT / "ingestion" / "feeds" / "pegel_poll.py"
    spec = importlib.util.spec_from_file_location("pegel_poll_for_watch", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Targets(unittest.TestCase):
    def test_station_list_mirrors_the_poller(self) -> None:
        self.assertEqual(tuple(s for s, _ in STATIONS), _poller().STATIONS)
        self.assertEqual(len(EU_POINT_IDS), 12)

    def test_city_names_one_point_or_gauge(self) -> None:
        self.assertEqual(watch_target(BUDAPEST)["points"], ["EU08"])
        self.assertEqual(watch_target(BUDAPEST)["stations"], [])
        self.assertEqual(watch_target(DRESDEN)["stations"], ["DRESDEN"])
        self.assertEqual(watch_target("Wien")["points"], ["EU07"])
        self.assertEqual(watch_target("Frankfurt (Oder)")["stations"], ["FRANKFURT1 (ODER)"])
        self.assertEqual(watch_target("Frankfurt")["stations"], ["FRANKFURT OSTHAFEN"])

    def test_river_names_every_gauge_and_point_on_it(self) -> None:
        t = watch_target("Is the Danube rising?")
        self.assertEqual(t["points"], ["EU07", "EU08"])
        self.assertEqual(t["stations"], ["REGENSBURG EISERNE BRÜCKE", "PASSAU DONAU"])

    def test_ambiguous_words_only_count_capitalised(self) -> None:
        self.assertIsNone(watch_target("rain oder schnee, what is the main risk?"))
        self.assertEqual(watch_target("the Main at night")["stations"][0], "FRANKFURT OSTHAFEN")

    def test_rhine_stays_on_the_rhine_path(self) -> None:
        self.assertFalse(is_watch_only(watch_target("Is the Rhine at Köln rising right now?")))
        self.assertFalse(is_watch_only(watch_target("Why are our Valencia sites at risk?")))
        self.assertTrue(is_watch_only(watch_target(DRESDEN)))

    def test_context_selection(self) -> None:
        self.assertEqual(watch_target("Is it at risk?", {"watch_point": "EU11"})["points"], ["EU11"])
        self.assertEqual(watch_target("Is it at risk?", {"station": "dresden"})["stations"], ["DRESDEN"])
        self.assertIsNone(watch_target("Is it at risk?", {"station": "BONN"}))

    def test_contract_lists_the_view(self) -> None:
        self.assertIn("eu_watch", CONTRACT_VIEWS)
        self.assertIn("eu_watch", OWNERS)


@mock.patch.object(settings, "live_data", True)
class Routing(unittest.TestCase):
    def test_watch_place_without_a_time_word_is_live(self) -> None:
        self.assertEqual(classify(DRESDEN)[0], "live")
        self.assertEqual(classify("And the Seine in Paris?")[0], "live")
        self.assertEqual(classify("The Elbe in Dresden in 2002?")[0], "event")
        self.assertEqual(classify("Why are our Valencia sites at risk?")[0], "event")

    def test_german_gauge_routes_to_the_german_event(self) -> None:
        self.assertEqual(route_event(DRESDEN, None)[0], "EMSR517")
        self.assertEqual(route_event("Passau now?", None)[0], "EMSR517")
        # A point outside Germany has no event of its own: the default event, live views.
        self.assertEqual(route_event(BUDAPEST, None)[0], "EMSR773")
        self.assertEqual(route_event("Paiporta or Dresden?", None)[0], "EMSR773")
        self.assertEqual(route_event("Is the Rhine at Köln rising?", None)[0], "EMSR517")

    def test_scope_takes_a_watch_place_live_and_declines_it_in_event_mode(self) -> None:
        node = scope.make()
        base = {"event_id": "EMSR773", "trace": []}
        live = node({**base, "request": {"question": BUDAPEST}})
        self.assertTrue(live["scope"]["in_scope"], live["scope"])
        past = node({**base, "request": {"question": "The Danube at Budapest in 2013?"}})
        self.assertFalse(past["scope"]["in_scope"])


def _with_readings() -> FakeZetaris:
    z = FakeZetaris()
    z._conn.execute(
        "UPDATE floodsense.eu_watch SET discharge_m3s = 1347.96, forecast_max_m3s = 2414.79, "
        "past30_median_m3s = 1136.63, band = 'above', as_of_date = '2026-10-27', "
        "source = 'Open-Meteo Flood API (GloFAS)' WHERE point_id = 'EU08'"
    )
    z._conn.execute(
        "INSERT INTO floodsense.gauge_levels VALUES ('DRESDEN', 'ELBE', '2026-10-27 08:00:00', "
        "66.0, 'ds_pegelonline')"
    )
    z._conn.commit()
    return z


@mock.patch.object(settings, "live_data", True)
class FullRun(unittest.TestCase):
    def _run(self, question: str, z: FakeZetaris | None = None) -> dict:
        deps = Deps(zetaris=z or _with_readings(), llm=FakeNightshift(), memory=NoMemory())
        return Runtime(deps=deps).start(RunRequest(question=question))

    def _cited(self, out: dict) -> set[str]:
        return {
            out["evidence"][x["query_id"]]["view"]
            for c in out["claims"]
            for x in c["citations"]
            if x["layer"] == "a"
        }

    def test_budapest_answers_from_eu_watch_with_query_ids(self) -> None:
        out = self._run(BUDAPEST)
        self.assertEqual(out["mode"]["mode"], "live")
        self.assertEqual(out["status"], "awaiting_approval", out.get("summary"))
        self.assertIn("floodsense.eu_watch", self._cited(out))
        self.assertIn("Danube at Budapest", out["summary"])
        self.assertIn("model band 'above'", out["summary"])
        self.assertIn("not an official warning", out["summary"])
        claim = next(c for c in out["claims"] if "Budapest" in c["text"])
        self.assertEqual(claim["numbers"], [1347.96, 2414.79, 1136.63])
        self.assertTrue(all(x.get("query_id") for x in claim["citations"] if x["layer"] == "a"))
        self.assertEqual(out["judge_summary"]["numeric_accuracy"], 1.0)

    def test_dresden_answers_from_the_gauge(self) -> None:
        out = self._run(DRESDEN)
        self.assertEqual(out["mode"]["mode"], "live")
        self.assertEqual(out["event_id"], "EMSR517")
        self.assertIn("floodsense.gauge_levels", self._cited(out))
        texts = " ".join(c["text"] for c in out["claims"])
        self.assertIn("DRESDEN (ELBE), PEGELONLINE gauge: 66 cm", texts)
        self.assertIn("Quelle: WSV, PEGELONLINE", texts)
        self.assertNotIn("Rhine gauges now", out["summary"])

    def test_seed_rows_say_there_is_no_reading(self) -> None:
        out = self._run(BUDAPEST, FakeZetaris())
        self.assertIn("no current GloFAS value", " ".join(c["text"] for c in out["claims"]))
        self.assertIn("No raised band", out["summary"])


if __name__ == "__main__":
    unittest.main()
