"""Forecast lane: router cues, the nodes on a fake Zetaris and fake engines, the outlook
guard (no number or place the claims lack), escalation, and the evals' path."""

from __future__ import annotations

import hashlib
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from floodsense_agents import router  # noqa: E402
from floodsense_agents.models import Claim, RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes import forecast  # noqa: E402
from floodsense_agents.retrieve_docs import RetrieveResult  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.watch import FORECAST_POINTS, STATIONS  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris, now_utc  # noqa: E402

KOELN = "Do the next 48 hours look safe at Köln?"
BUDAPEST = "Will the Danube at Budapest rise this week?"


def _zetaris(koeln_level: float | None = 412.0) -> FakeZetaris:
    """The fake plus a live Köln reading, a Budapest eu_watch row and Ahr seed rain."""
    z = FakeZetaris()
    with z._lock:
        if koeln_level is not None:
            z._conn.execute(
                "INSERT INTO floodsense.gauge_levels VALUES (?,?,?,?,?)",
                ("KÖLN", "RHEIN", now_utc(), koeln_level, "pegelonline"),
            )
        z._conn.execute(
            "UPDATE floodsense.eu_watch SET discharge_m3s=2210, forecast_max_m3s=2600, "
            "past30_median_m3s=2000, band='below' WHERE point_id='EU08'"
        )
        # Altenahr: 12 hours of 6.5 mm on 14 Jul 2021 (test rows, not the seed extract).
        z._conn.execute("DELETE FROM floodsense_seed.hazard_timeline WHERE point_id='AHR01'")
        for h in range(12):
            z._conn.execute(
                "INSERT INTO floodsense_seed.hazard_timeline VALUES (?,?,?,?,?)",
                ("AHR01", f"2021-07-14T{h:02d}:00:00Z", 6.5, 120.0 + h, None),
            )
        z._conn.commit()
    return z


class FakeMemory:
    """Fake engines: one seeded memory about Köln, one about Valencia."""

    def __init__(self) -> None:
        self.asked: list[dict] = []

    def recall(self, request):
        self.asked.append(request)
        return [
            {
                "memory_id": "m1",
                "run_id": "demo-seed-1",
                "claim_id": "C1",
                "content": "KÖLN (RHEIN) stayed below mean high water in the last approved run.",
                "provenance": {
                    "label": "run demo-seed-1 approved by demo-seed",
                    "learned_at": "2026-10-26",
                },
                "tags": ["entity:demo-seed", "event:EMSR517"],
            },
            {
                "memory_id": "m2",
                "run_id": "r2",
                "content": "Paiporta flooded in 2024.",
                "provenance": {"label": "run r2 approved by ana"},
                "tags": ["event:EMSR773"],
            },
        ]

    def store(self, *a, **k):
        return None


def _passage() -> dict:
    text = "On 14 July 2021 heavy rain over the Eifel led to an extreme flood on the Ahr."
    sha = hashlib.sha256(text.encode()).hexdigest()
    return {
        "layer": "c",
        "query_id": "doc-q1",
        "title": "July 2021 flood, Part 1",
        "source_url": "https://doi.org/10.5194/nhess-23-525-2023",
        "publisher": "NHESS",
        "licence": "CC BY 4.0",
        "attribution": "Mohr et al. (2023)",
        "locator": {"page": 3, "paragraph": 2, "lines": "1-1"},
        "quote": text,
        "content_sha256": sha,
        "storage": "full_text",
        "chunk_id": "nhess-23-525/p3/2",
        "text": text,
        "text_sha256": sha,
    }


def _outlook(text: str) -> FakeNightshift:
    return FakeNightshift({"forecast_outlook": lambda s, u: '{"outlook": "%s"}' % text})


@mock.patch.object(settings, "live_data", True)
class RouterForecastCues(unittest.TestCase):
    def test_forecast_cues_with_a_watched_place(self) -> None:
        for q, place in [
            (KOELN, "KÖLN"),
            (BUDAPEST, "Budapest"),
            ("What is the rain forecast for Dresden?", "DRESDEN"),
            ("Will Paiporta flood tomorrow?", "Paiporta"),
            ("Wie wird der Rhein in Bonn morgen?", "BONN"),
            ("Steigt die Elbe in Dresden in den nächsten 48 Stunden?", "DRESDEN"),
            ("¿Lloverá en Valencia mañana?", "Paiporta"),
            ("Is the Vltava at Prague going to rise over the next 3 days?", "Prague"),
        ]:
            lane, why = router.rules(q)
            self.assertEqual(lane, "forecast", q)
            self.assertIn(place, why, q)

    def test_present_questions_stay_quick(self) -> None:
        for q in ("How high is the Rhine at Köln?", "Is the Danube at Budapest rising?"):
            self.assertEqual(router.rules(q)[0], "quick", q)

    def test_why_and_the_past_go_full(self) -> None:
        for q in (
            "Why will the Rhine at Köln rise tomorrow?",
            "Explain the forecast for Valencia next 48 hours",
            "What happened in Valencia on 29 October 2024?",
        ):
            self.assertEqual(router.rules(q)[0], "full", q)

    def test_greeting_is_not_tomorrow_and_no_place_is_not_forecast(self) -> None:
        self.assertNotEqual(router.rules("Guten Morgen, Köln")[0], "forecast")
        self.assertNotEqual(router.rules("Will it rain tomorrow?")[0], "forecast")

    def test_explicit_requests_and_flags_go_full(self) -> None:
        for req in (
            RunRequest(question=KOELN, event_id="EMSR517"),
            RunRequest(question=KOELN, replay_ts="2021-07-14T18:00:00Z"),
            RunRequest(question=KOELN, mode="event"),
        ):
            self.assertEqual(router.route(req)["lane"], "full")
        with mock.patch.dict("os.environ", {"FF_FORECAST_LANE": "false"}):
            self.assertNotEqual(router.route(RunRequest(question=KOELN))["lane"], "forecast")

    def test_live_data_off_means_full(self) -> None:
        with mock.patch.object(settings, "live_data", False):
            self.assertEqual(router.route(RunRequest(question=KOELN))["lane"], "full")

    def test_every_eval_item_stays_full(self) -> None:
        try:
            import yaml
        except ImportError:
            self.skipTest("pyyaml not installed")
        n = 0
        for f in sorted((ROOT / "evals").glob("*.yaml")):
            spec = yaml.safe_load(f.read_text(encoding="utf-8"))
            for item in spec.get("items") or []:
                req = RunRequest(
                    question=item["question"],
                    event_id=spec.get("event_id"),
                    replay_ts=item.get("replay_ts"),
                )
                self.assertEqual(router.route(req)["lane"], "full", item["id"])
                n += 1
        self.assertGreater(n, 10)


class PlacesTest(unittest.TestCase):
    def test_all_45_places_and_the_migration_agree(self) -> None:
        self.assertEqual(len(FORECAST_POINTS), 45)
        kinds = [p[1] for p in FORECAST_POINTS]
        self.assertEqual(
            (kinds.count("gauge"), kinds.count("eu"), kinds.count("valencia")), (26, 11, 8)
        )
        self.assertEqual([p[2] for p in FORECAST_POINTS[:26]], [s for s, _ in STATIONS])
        mig = (ROOT / "zetaris" / "migrations" / "071_create_view_weather_forecast.sql").read_text(
            encoding="utf-8"
        )
        rows = re.findall(
            r"\((\d+), '(\w+)', '(\w+)', '[^']*', '[^']*', (-?[\d.]+), (-?[\d.]+)\)", mig
        )
        self.assertEqual(
            [(int(i), pid, kind, float(lat), float(lon)) for i, pid, kind, lat, lon in rows],
            [(i, p[0], p[1], p[5], p[6]) for i, p in enumerate(FORECAST_POINTS)],
        )
        rest = (
            ROOT / "zetaris" / "migrations" / "070_create_rest_table_weather_forecast_live.sql"
        ).read_text(encoding="utf-8")
        lats = re.search(r"latitude=([-\d.,]+)", rest).group(1).split(",")
        self.assertEqual([float(x) for x in lats], [p[5] for p in FORECAST_POINTS])
        self.assertIn("models=icon_seamless", rest)

    @mock.patch.object(settings, "live_data", True)
    def test_every_place_reads_its_forecast_row(self) -> None:
        z = FakeZetaris()
        deps = Deps(zetaris=z, llm=FakeNightshift(), memory=NoMemory())
        node = forecast.make_forecast_data(deps)
        for p in FORECAST_POINTS:
            with mock.patch.object(forecast, "_asked", return_value=[p]):
                out = node({"run_id": "t", "trace": []})
            place = out["live_findings"]["forecast_places"][0]
            self.assertIn("weather", place, p[0])
            ev = out["evidence"][place["weather"]]
            self.assertEqual(ev["rows_sample"][0]["point_id"], p[0])

    def test_memories_name_the_place_and_state_something(self) -> None:
        koeln = next(p for p in FORECAST_POINTS if p[0] == "PEG07")
        mems = [
            {"memory_id": "a", "content": "No supporting evidence was provided about KÖLN."},
            {"memory_id": "b", "content": "Paiporta flooded."},
            {"memory_id": "c", "content": "KÖLN read 412 cm.", "provenance": {"label": "run r by ana"}},
        ]
        rows = forecast._memory_rows(mems, koeln)
        self.assertEqual([r["memory_id"] for r in rows], ["c"])
        self.assertEqual(rows[0]["reviewer"], "ana")
        self.assertFalse(rows[0]["seeded"])

    def test_place_resolution(self) -> None:
        got = lambda q, c=None: [p[0] for p in forecast.forecast_places(q, c)]  # noqa: E731
        self.assertEqual(got(KOELN), ["PEG07"])
        self.assertEqual(got(BUDAPEST), ["EU08"])
        self.assertEqual(got("Will Chiva flood tomorrow?"), ["VAL07"])
        self.assertEqual(got("Valencia next 48 hours"), ["VAL01", "VAL07"])
        self.assertEqual(len(got("Will the Danube rise this week?")), forecast.MAX_PLACES)
        self.assertEqual(got("next 48 hours?", {"station": "KÖLN"}), ["PEG07"])


@mock.patch.object(settings, "live_data", True)
class ForecastLaneTest(unittest.TestCase):
    def _run(self, question=KOELN, z=None, llm=None, memory=None, docs=None):
        deps = Deps(
            zetaris=z or _zetaris(),
            llm=llm or _outlook("The next two days look calm at KÖLN. Rain stays light."),
            memory=memory or NoMemory(),
            retrieve_docs=docs,
        )
        return Runtime(deps=deps).start(RunRequest(question=question))

    @mock.patch.object(settings, "ff_rag_docs", True)
    def test_koeln_claims_history_memory_passage_and_outlook(self) -> None:
        mem = FakeMemory()
        docs = mock.Mock(return_value=RetrieveResult([_passage()], None))
        snap = self._run(memory=mem, docs=docs)
        self.assertEqual(
            (snap["lane"], snap["status"]), ("forecast", "answered"), snap["router_reason"]
        )
        self.assertEqual(
            [e["node"] for e in snap["trace"]],
            ["router", "scope", "forecast_data", "history", "forecast_answer", "judge"],
        )
        self.assertTrue(snap["judge_summary"]["passes"], snap["judge"])
        self.assertEqual(snap["approval"]["status"], "not_reached")
        texts = [c["text"] for c in snap["claims"]]
        self.assertTrue(
            texts[0].startswith("KÖLN: forecast precipitation for the next 48 hours is 4.8 mm")
        )
        self.assertTrue(any("level 412 cm" in t for t in texts))
        past = next(t for t in texts if t.startswith("Past pattern"))
        self.assertIn("reached 78 mm at Altenahr", past)
        self.assertIn("at KÖLN is 4.8 mm", past)
        memory = next(t for t in texts if t.startswith("Approved memory"))
        self.assertIn("demo seed", memory)
        self.assertNotIn("Paiporta", memory)  # only the memory that names the place
        self.assertTrue(any(t.startswith("July 2021 flood, Part 1") for t in texts))
        docs.assert_called_once()
        self.assertIn("KÖLN flood", docs.call_args.args[0])
        self.assertEqual(docs.call_args.args[2], {"event_id": "EMSR517"})
        # every claim cites only its own evidence
        views = {
            c["claim_id"]: {
                snap["evidence"][x["query_id"]]["view"] for x in c["citations"] if x.get("query_id")
            }
            for c in snap["claims"]
        }
        self.assertEqual(views["F1"], {"floodsense.weather_forecast"})
        self.assertEqual(views["F2"], {"floodsense.gauge_levels"})
        self.assertEqual(
            views["F3"], {"floodsense_seed.hazard_timeline", "floodsense.weather_forecast"}
        )
        self.assertIn({"hmem.recall"}, views.values())
        self.assertIn({"PGVECTOR_RAG.chunks"}, views.values())
        fc = snap["forecast"]
        self.assertEqual(fc["status"], "Normal")
        self.assertEqual(fc["outlook_label"], "Outlook (model-written)")
        self.assertIn(
            "Outlook (model-written): The next two days look calm at KÖLN.", snap["summary"]
        )
        self.assertIn("not an official warning; follow DWD", fc["disclaimer"])
        self.assertTrue(snap["summary"].endswith(fc["disclaimer"]))

    def test_budapest_reads_eu_watch_and_names_the_national_service(self) -> None:
        snap = self._run(BUDAPEST, llm=FakeNightshift())
        self.assertEqual(
            (snap["lane"], snap["status"]), ("forecast", "answered"), snap["router_reason"]
        )
        self.assertIn("forecast maximum 2600 m3/s", " ".join(c["text"] for c in snap["claims"]))
        self.assertIn("HungaroMet", snap["forecast"]["disclaimer"])
        self.assertIsNone(snap["forecast"]["outlook"])
        self.assertIn("no outlook in the reply", snap["forecast"]["outlook_note"])

    def test_chiva_rain_is_a_warning(self) -> None:
        snap = self._run("Will Chiva flood in the next 48 hours?", llm=FakeNightshift())
        self.assertEqual(snap["forecast"]["status"], "Warning")
        self.assertIn("Past pattern: before the October 2024 Valencia DANA flood", snap["summary"])
        self.assertIn("AEMET", snap["forecast"]["disclaimer"])

    def test_outlook_with_a_number_the_claims_lack_is_dropped(self) -> None:
        snap = self._run(llm=_outlook("Up to 80 mm may fall at KÖLN. Stay alert."))
        self.assertIsNone(snap["forecast"]["outlook"])
        self.assertIn("names the number 80", snap["forecast"]["outlook_note"])
        self.assertNotIn("Outlook (model-written)", snap["summary"])
        self.assertEqual(snap["status"], "answered")

    def test_outlook_with_a_place_the_claims_lack_is_dropped(self) -> None:
        snap = self._run(llm=_outlook("Calm at KÖLN. Bonn looks calm too."))
        self.assertIsNone(snap["forecast"]["outlook"])
        self.assertIn("names 'Bonn'", snap["forecast"]["outlook_note"])

    def test_outlook_guard_unit(self) -> None:
        claims = [
            Claim(
                claim_id="F1", text="KÖLN: forecast precipitation for the next 48 hours is 4.8 mm."
            )
        ]
        self.assertTrue(forecast.outlook_ok("About 4.8 mm at Köln in 48 hours. Calm.", claims)[0])
        self.assertFalse(forecast.outlook_ok("About 5 mm at Köln.", claims)[0])
        self.assertFalse(forecast.outlook_ok("Calm. Calm. Calm.", claims)[0])
        self.assertFalse(forecast.outlook_ok("This is an official warning for Köln.", claims)[0])
        self.assertFalse(forecast.outlook_ok("", claims)[0])

    def test_outlook_numbers_are_all_claim_numbers(self) -> None:
        snap = self._run(
            llm=_outlook("Rain at KÖLN stays near 4.8 mm over 48 hours. The level is 412 cm.")
        )
        outlook = snap["forecast"]["outlook"]
        self.assertTrue(outlook)
        from floodsense_agents.nodes.investigator import numbers_in

        stated = set(numbers_in(" ".join(c["text"] for c in snap["claims"])))
        self.assertTrue(set(numbers_in(outlook)) <= stated)

    def test_outlook_failure_keeps_the_answer(self) -> None:
        class Boom:
            def complete(self, *a, **k):
                raise RuntimeError("502")

        snap = self._run(llm=Boom())
        self.assertEqual(snap["status"], "answered")
        self.assertIn("fast lane failed", snap["forecast"]["outlook_note"])

    def test_no_forecast_rows_escalates(self) -> None:
        z = _zetaris(koeln_level=None)
        with z._lock:
            z._conn.execute("DELETE FROM floodsense.weather_forecast WHERE point_id='PEG07'")
            z._conn.commit()
        snap = self._run(z=z, llm=FakeNightshift())
        self.assertEqual(snap["lane"], "full")
        self.assertIn("escalated: no forecast rows", snap["router_reason"])
        self.assertIn("watchers", [e["node"] for e in snap["trace"]])

    def test_a_judge_flag_escalates(self) -> None:
        def wrong(p, row):
            return ("KÖLN: forecast precipitation 999 mm.", [999.0]), 999.0, None

        with mock.patch.object(forecast, "weather_claim", wrong):
            snap = self._run(llm=FakeNightshift())
        self.assertEqual(snap["lane"], "full")
        self.assertIn("escalated: judge flagged F1", snap["router_reason"])
        self.assertEqual(snap["forecast"], {})


if __name__ == "__main__":
    unittest.main()
