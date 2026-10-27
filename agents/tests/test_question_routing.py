"""A question that names one event's places routes there, over the screen context."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from floodsense_agents.events import question_event, route_event  # noqa: E402
from floodsense_agents.nodes import scope  # noqa: E402

AHR_Q = "What is the current water level near Ahr Valley? Is it under flooding risk?"
PAIPORTA = {"role": "citizen", "page": "overview", "point_id": "VAL01"}


class QuestionBeatsContext(unittest.TestCase):
    def test_ahr_question_on_paiporta_overview_routes_to_ahr(self) -> None:
        ev, why = route_event(AHR_Q, None, PAIPORTA)
        self.assertEqual(ev, "EMSR517")
        self.assertIn("question names", why)

    def test_routed_ahr_question_passes_the_scope_gate(self) -> None:
        ev, _ = route_event(AHR_Q, None, PAIPORTA)
        self.assertTrue(scope.check(AHR_Q, ev)["in_scope"])

    def test_valencia_town_on_an_ahr_context_routes_to_valencia(self) -> None:
        ev, _ = route_event("Is Paiporta flooding?", None, {"point_id": "AHR01"})
        self.assertEqual(ev, "EMSR773")

    def test_context_decides_when_no_place_is_named(self) -> None:
        self.assertEqual(route_event("Am I at risk?", None, {"point_id": "AHR01"})[0], "EMSR517")
        self.assertEqual(route_event("Am I at risk?", None, PAIPORTA)[0], "EMSR773")

    def test_both_events_named_falls_back_to_context(self) -> None:
        q = "Compare Paiporta and the Ahr valley"
        self.assertIsNone(question_event(q))
        self.assertEqual(route_event(q, None, {"point_id": "AHR01"})[0], "EMSR517")

    def test_explicit_event_id_still_stands(self) -> None:
        self.assertEqual(route_event(AHR_Q, "EMSR773", PAIPORTA)[0], "EMSR773")


class WarmDecline(unittest.TestCase):
    def test_explicit_valencia_decline_is_warm_and_honest(self) -> None:
        verdict = scope.check(AHR_Q, "EMSR773")
        self.assertFalse(verdict["in_scope"])
        self.assertEqual(verdict["elsewhere"], "EMSR517")
        r = verdict["reason"]
        self.assertTrue(r.startswith("That's about the Ahr valley flood (July 2021)"), r)
        self.assertIn("I'm looking at Valencia (EMSR773) here", r)
        self.assertIn("Switch to the Ahr case and I'll answer it.", r)
        self.assertIn("no data on", r)

    def test_reverse_direction(self) -> None:
        verdict = scope.check("How much rain fell at Chiva?", "EMSR517")
        self.assertEqual(verdict["elsewhere"], "EMSR773")
        self.assertIn("Valencia DANA flood (October 2024)", verdict["reason"])


if __name__ == "__main__":
    unittest.main()
