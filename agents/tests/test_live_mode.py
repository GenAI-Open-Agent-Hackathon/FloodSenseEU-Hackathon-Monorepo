"""Live mode: hazard_now instead of the event window. Fake Zetaris, fake Nightshift."""

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

from floodsense_agents.events import spec  # noqa: E402
from floodsense_agents.live import classify, resolve_mode  # noqa: E402
from floodsense_agents.models import RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes import investigator, skeptic, watchers  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402

QUESTION = "Is any Valencia point at risk in the next 48 hours?"
LIVE = {"mode": "live", "explicit": None, "reason": "test"}
EVENT = {"mode": "event", "explicit": None, "reason": "test"}


def deps(z=None) -> Deps:
    return Deps(zetaris=z or FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())


def quiet() -> FakeZetaris:
    """No point crosses anything: forecast discharge 5 m3/s, rain 1 mm/h everywhere."""
    z = FakeZetaris()
    z._conn.execute("UPDATE floodsense.hazard_now SET discharge_m3s = 5, rain_mm = 1")
    return z


def state(mode, question=QUESTION) -> dict:
    ev = spec("EMSR773")
    return {
        "run_id": "t",
        "event_id": ev.event_id,
        "event": ev.as_dict(),
        "request": {"question": question, "lang": "en"},
        "replay_ts": None,
        "mode": mode,
        "trace": [],
        "evidence": {},
        "provenance": [],
    }


class Resolution(unittest.TestCase):
    def test_explicit_mode_wins(self) -> None:
        self.assertEqual(resolve_mode({"question": QUESTION, "mode": "event"})["mode"], "event")
        self.assertEqual(resolve_mode({"question": "Why?", "mode": "live"})["mode"], "live")

    def test_classifier_en_es_de(self) -> None:
        for q in (
            QUESTION,
            "What is the river doing right now?",
            "Any rain tonight in Chiva?",
            "Show me the forecast for Paiporta",
            "¿Hay riesgo de inundación mañana en Paiporta?",
            "¿Qué dice el pronóstico para hoy?",
            "Wie ist die Vorhersage für morgen?",
            "Was passiert jetzt in Valencia?",
        ):
            self.assertEqual(classify(q)[0], "live", q)
        for q in ("Why were our Valencia sites flooded?", "What happened at Paiporta in 2024?"):
            self.assertEqual(classify(q)[0], "event", q)

    def test_replay_ts_forces_event(self) -> None:
        got = resolve_mode({"question": QUESTION, "mode": "live", "replay_ts": "2024-10-29T16:00:00Z"})
        self.assertEqual(got["mode"], "event")
        self.assertIn("replay_ts", got["reason"])

    def test_request_accepts_mode(self) -> None:
        self.assertIsNone(RunRequest(question="q").mode)
        self.assertEqual(RunRequest(question="q", mode="live").mode, "live")
        with self.assertRaises(ValueError):
            RunRequest(question="q", mode="later")


@mock.patch.object(settings, "live_data", True)
class Nodes(unittest.TestCase):
    def test_watchers_target_hazard_now_in_live_and_timeline_in_event(self) -> None:
        live = watchers.make(deps())(state(LIVE))
        sqls = [e["sql"] for e in live["evidence"].values() if e["view"] != "floodsense.provenance"]
        self.assertTrue(sqls and all("floodsense.hazard_now" in q for q in sqls), sqls)
        kinds = {(a["kind"], a["horizon"]) for a in live["anomalies"]}
        self.assertIn(("discharge", "forecast"), kinds)
        self.assertTrue(all("at 20" in a["why"] for a in live["anomalies"]))
        event = watchers.make(deps())(state(EVENT))
        sqls = [e["sql"] for e in event["evidence"].values() if e["view"] != "floodsense.provenance"]
        self.assertTrue(all("hazard_timeline" in q for q in sqls), sqls)

    def test_quiet_forecast_is_a_result(self) -> None:
        out = watchers.make(deps(quiet()))(state(LIVE))
        self.assertEqual(out["anomalies"], [])
        s = state(LIVE)
        s.update(evidence=out["evidence"], provenance=out["provenance"])
        inv = investigator.make(deps(quiet()))(s)
        self.assertIn("No point's forecast discharge reaches 100 m3/s", inv["summary"])
        self.assertFalse(inv["live_findings"]["discharge_crosses"])
        s.update(inv)
        sk = skeptic.make(deps(quiet()))(s)
        h2 = next(h for h in sk["hypotheses"] if h["id"] == "H2")
        self.assertEqual(h2["status"], "supported", h2["rationale"])

    def test_investigator_cites_hazard_now(self) -> None:
        z = FakeZetaris()
        w = watchers.make(deps(z))(state(LIVE))
        s = state(LIVE)
        s.update(evidence=w["evidence"], provenance=w["provenance"])
        out = investigator.make(deps(z))(s)
        ev = out["evidence"]
        rivers = [c for c in out["claims"] if c["hypothesis_id"] in ("H1", "H2")]
        self.assertTrue(rivers)
        for c in rivers:
            qids = [x["query_id"] for x in c["citations"] if x["layer"] == "a"]
            self.assertTrue(qids and all(ev[q]["view"] == "floodsense.hazard_now" for q in qids))
        texts = " ".join(c["text"] for c in rivers)
        self.assertIn("Forecast", texts)
        self.assertIn("Past days", texts)
        self.assertRegex(texts, r"\(in \d+ h\)")
        self.assertEqual(out["live_findings"]["crossing_points"], ["VAL01"])
        event = investigator.make(deps())(state(EVENT))
        views = {e["view"] for e in event["evidence"].values()}
        self.assertNotIn("floodsense.hazard_now", views)
        self.assertIn("floodsense.hazard_timeline", views)

    def test_skeptic_counter_checks_hazard_now(self) -> None:
        z = FakeZetaris()
        s = state(LIVE)
        s.update(investigator.make(deps(z))(s))
        out = skeptic.make(deps(z))(s)
        for h in out["hypotheses"]:
            self.assertEqual(h["status"], "supported", h["rationale"])
            if h["link"] in ("rain->catchment", "catchment->river"):
                views = {out["evidence"][q]["view"] for q in h["evidence"]}
                self.assertEqual(views, {"floodsense.hazard_now"})

    def test_seed_schema_has_no_live_rows(self) -> None:
        with mock.patch.object(settings, "live_data", False):
            out = watchers.make(deps())(state(LIVE))
            self.assertEqual(out["anomalies"], [])
            self.assertTrue(all("horizon IN ('past', 'forecast')" in e["sql"]
                                for e in out["evidence"].values() if "hazard_now" in e["view"]))


@mock.patch.object(settings, "live_data", True)
class FullRun(unittest.TestCase):
    def _run(self, z, question=QUESTION, **kw):
        return Runtime(deps=deps(z)).start(RunRequest(question=question, **kw))

    def test_live_run_awaits_approval_citing_hazard_now(self) -> None:
        out = self._run(FakeZetaris())
        self.assertEqual(out["status"], "awaiting_approval")
        self.assertEqual(out["mode"]["mode"], "live")
        self.assertTrue(out["summary"].startswith("Live data"))
        self.assertIn("Paiporta (VAL01) is forecast", out["summary"])
        cited = {
            out["evidence"][x["query_id"]]["view"]
            for c in out["claims"]
            for x in c["citations"]
            if x["layer"] == "a"
        }
        self.assertIn("floodsense.hazard_now", cited)
        self.assertNotIn("floodsense.hazard_timeline", cited)
        self.assertEqual(out["judge_summary"]["numeric_accuracy"], 1.0)
        scope = next(t for t in out["trace"] if t["node"] == "scope")
        self.assertIn("mode live", scope["summary"])
        footprint = [c["text"] for c in out["claims"] if c["hypothesis_id"] in ("H3", "H4")]
        self.assertTrue(footprint and all("historical" in t.lower() for t in footprint))

    def test_quiet_live_run_still_answers(self) -> None:
        out = self._run(quiet())
        self.assertEqual(out["status"], "awaiting_approval")
        self.assertIn("No point's forecast discharge reaches 100 m3/s", out["summary"])
        self.assertEqual(out["judge_summary"]["numeric_accuracy"], 1.0)

    def test_event_question_stays_event(self) -> None:
        out = self._run(FakeZetaris(), question="Why are our Valencia sites at risk?")
        self.assertEqual(out["mode"]["mode"], "event")
        views = {e["view"] for e in out["evidence"].values()}
        self.assertNotIn("floodsense.hazard_now", views)


if __name__ == "__main__":
    unittest.main()
