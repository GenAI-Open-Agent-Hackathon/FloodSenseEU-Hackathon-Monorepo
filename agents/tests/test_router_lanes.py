"""Router agent: rules, the mocked fast lane, the quick lane and its escalation."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from floodsense_agents import router  # noqa: E402
from floodsense_agents.models import RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris, now_utc  # noqa: E402

_QID = re.compile(r"query_id=(\S+) view=(\S+)")


def _qid(user: str, view: str) -> str:
    return next(q for q, v in _QID.findall(user) if v.endswith(view))


def _zetaris_with_koeln() -> FakeZetaris:
    z = FakeZetaris()
    with z._lock:
        z._conn.execute(
            "INSERT INTO floodsense.gauge_levels VALUES (?,?,?,?,?)",
            ("KÖLN", "RHEIN", now_utc(), 412.0, "pegelonline"),
        )
        z._conn.commit()
    return z


class _Raising:
    def complete(self, lane, system, user, *, json=True):
        raise RuntimeError("gateway 502")


class RouterRulesTest(unittest.TestCase):
    def test_live_questions_with_a_place_go_quick(self) -> None:
        for q, place in [
            ("How high is the Rhine at Köln?", "RHINE"),
            ("Is any Valencia point at risk in the next 48 hours?", "VALENCIA"),
            ("Is the Danube at Budapest rising?", "DANUBE"),
        ]:
            lane, why = router.rules(q)
            self.assertEqual(lane, "quick", q)
            self.assertIn(place, why)

    def test_deep_words_go_full(self) -> None:
        for q in [
            "Why is the Rhine at Köln rising?",
            "Which insured sites are exposed in Valencia right now?",
            "Replay the Ahr flood",
            "What happened in Valencia on 29 October 2024?",
            "Draft alerts for the policyholders in Valencia now",
            "What does the EFAS bulletin say about the Danube today?",
        ]:
            self.assertEqual(router.rules(q)[0], "full", q)

    def test_ambiguous_is_none(self) -> None:
        self.assertIsNone(router.rules("Is it rising now?")[0])
        self.assertIsNone(router.rules("Tell me about Valencia")[0])

    def test_route_records_a_reason(self) -> None:
        got = router.route(RunRequest(question="How high is the Rhine at Köln?"))
        self.assertEqual(got["lane"], "quick")
        self.assertEqual(got["model_id"], "rules")
        self.assertTrue(got["reason"].startswith("chose quick: live level question about"))

    def test_explicit_requests_stay_full_for_the_evals(self) -> None:
        q = "How high is the Rhine at Köln?"
        for req in (
            RunRequest(question=q, event_id="EMSR517"),
            RunRequest(question=q, replay_ts="2021-07-14T18:00:00Z"),
            RunRequest(question=q, doc_query="EFAS bulletin"),
            RunRequest(question=q, mode="event"),
        ):
            self.assertEqual(router.route(req)["lane"], "full")

    def test_flag_off(self) -> None:
        with mock.patch.dict("os.environ", {"FF_QUICK_LANE": "false"}):
            self.assertEqual(router.route(RunRequest(question="Rhine level at Köln now?"))["lane"], "full")


class RouterModelTest(unittest.TestCase):
    def test_model_decides_only_ambiguous(self) -> None:
        llm = FakeNightshift({"router": lambda s, u: '{"lane": "quick"}'})
        got = router.route(RunRequest(question="Is it rising now?"), llm)
        self.assertEqual((got["lane"], got["model_id"]), ("quick", "fake-fast"))
        self.assertEqual(llm.calls[0][:2], ("fast", "router"))
        router.route(RunRequest(question="How high is the Rhine at Köln?"), llm)
        self.assertEqual(len(llm.calls), 1)  # rules decided the second one

    def test_failure_or_bad_label_means_full(self) -> None:
        self.assertEqual(router.route(RunRequest(question="Is it rising now?"), _Raising())["lane"], "full")
        bad = FakeNightshift({"router": lambda s, u: '{"lane": "sideways"}'})
        self.assertEqual(router.route(RunRequest(question="Is it rising now?"), bad)["lane"], "full")


def _koeln_answer(number: float):
    def answer(system: str, user: str) -> str:
        qid = _qid(user, "gauge_levels")
        return json.dumps(
            {
                "claims": [
                    {"text": f"The Rhine at KÖLN reads {number:g} cm.", "query_ids": [qid]},
                    {"text": "This is the latest PEGELONLINE reading for KÖLN.", "query_ids": [qid]},
                ]
            }
        )

    return answer


@mock.patch.object(settings, "live_data", True)
class QuickLaneTest(unittest.TestCase):
    def _run(self, llm, question="How high is the Rhine at Köln?"):
        deps = Deps(zetaris=_zetaris_with_koeln(), llm=llm, memory=NoMemory())
        return Runtime(deps=deps).start(RunRequest(question=question))

    def test_quick_answer_passes_the_judge(self) -> None:
        llm = FakeNightshift({"quick_answer": _koeln_answer(412)})
        snap = self._run(llm)
        self.assertEqual(snap["lane"], "quick")
        self.assertEqual(snap["status"], "answered")
        self.assertTrue(snap["router_reason"].startswith("chose quick"))
        self.assertTrue(snap["judge_summary"]["passes"])
        self.assertEqual(snap["approval"]["status"], "not_reached")
        self.assertEqual(snap["playbook"], [])
        nodes = [e["node"] for e in snap["trace"]]
        self.assertEqual(nodes, ["router", "scope", "live_watch", "quick_answer", "judge"])
        self.assertIn("live level question about", snap["trace"][0]["summary"])
        for claim in snap["claims"]:
            self.assertTrue(claim["citations"])
            self.assertIn(claim["citations"][0]["query_id"], snap["evidence"])
        # One fast-lane call answered; nothing went to the deep lane.
        self.assertEqual([c[:2] for c in llm.calls], [("fast", "quick_answer")])

    def test_judge_flag_escalates_to_the_full_lane(self) -> None:
        llm = FakeNightshift({"quick_answer": _koeln_answer(999)})
        snap = self._run(llm)
        self.assertEqual(snap["lane"], "full")
        self.assertIn("escalated: judge flagged Q1", snap["router_reason"])
        nodes = [e["node"] for e in snap["trace"]]
        self.assertIn("watchers", nodes)
        esc = [e for e in snap["trace"] if e["node"] == "router" and "escalated" in e["summary"]]
        self.assertEqual(len(esc), 1)
        self.assertEqual(snap["status"], "awaiting_approval")
        self.assertFalse(any(c["claim_id"].startswith("Q") for c in snap["claims"]))

    def test_missing_data_escalates(self) -> None:
        deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
        snap = Runtime(deps=deps).start(RunRequest(question="How high is the Rhine at Köln?"))
        self.assertEqual(snap["lane"], "full")
        self.assertIn("escalated: no live rows", snap["router_reason"])

    def test_valencia_forecast_from_hazard_now(self) -> None:
        def answer(system: str, user: str) -> str:
            qid = _qid(user, "hazard_now")
            return json.dumps(
                {
                    "claims": [
                        {"text": "Paiporta has a forecast peak discharge of 180 m3/s.", "query_ids": [qid]},
                        {"text": "Chiva has a forecast hour of 34 mm rain.", "query_ids": [qid]},
                    ]
                }
            )

        snap = self._run(
            FakeNightshift({"quick_answer": answer}),
            "Is any Valencia point at risk in the next 48 hours?",
        )
        self.assertEqual((snap["lane"], snap["status"]), ("quick", "answered"), snap["router_reason"])


if __name__ == "__main__":
    unittest.main()
