"""The API projection of a graph run validates against the shared schema.

No live Nightshift or Zetaris. The run is the in-process fake graph, the
same one the proxy test uses.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "agents"))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from jsonschema import Draft202012Validator  # noqa: E402
from jsonschema.exceptions import ValidationError  # noqa: E402

from app.project import project_run  # noqa: E402

SCHEMA = json.loads(
    (ROOT / "contracts" / "schemas" / "floodsense.schema.json").read_text(encoding="utf-8")
)


def validator_for(def_name: str) -> Draft202012Validator:
    wrapper = {
        "$schema": SCHEMA["$schema"],
        "$defs": SCHEMA["$defs"],
        "$ref": f"#/$defs/{def_name}",
    }
    return Draft202012Validator(wrapper, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _fake_run() -> dict:
    from fastapi.testclient import TestClient
    from langgraph.checkpoint.memory import MemorySaver

    from floodsense_agents import __main__ as service
    from floodsense_agents.graph import build_graph
    from floodsense_agents.nightshift import FakeNightshift
    from floodsense_agents.runtime import Runtime
    from floodsense_agents.state import Deps, NoMemory
    from floodsense_agents.zetaris import FakeZetaris

    deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
    service.set_runtime(Runtime(graph=build_graph(deps, MemorySaver(), ff_judge=True), deps=deps))
    client = TestClient(service.app)
    response = client.post(
        "/runs", json={"question": "Which sites are exposed?", "event_id": "EMSR773"}
    )
    if response.status_code != 201:
        raise AssertionError(response.text)
    return response.json()


class ProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph_run = _fake_run()
        cls.projected = project_run(cls.graph_run)
        if cls.projected is None:
            raise AssertionError("project_run returned nothing for a completed fake run")

    def test_answer_evidence_playbook_judge_and_approval_match_the_schema(self) -> None:
        answer = self.projected["answer"]
        self.assertNotEqual(answer["served_from"], "live")
        self.assertEqual(answer["served_from"], "replay")
        self.assertIsNotNone(answer["cached_at"])
        for name, payload in (
            ("answer", answer),
            ("judge", answer["judge"]),
        ):
            try:
                validator_for(name).validate(payload)
            except ValidationError as e:
                self.fail(f"{name} failed schema: {e.message} at {list(e.absolute_path)}")
        self.assertTrue(answer["evidence"])
        self.assertTrue(answer["playbook_actions"])
        self.assertTrue(self.projected["approvals"])
        for row in answer["evidence"]:
            validator_for("evidence").validate(row)
            self.assertNotIn("source", row)
            self.assertNotIn("error", row)
        for row in answer["playbook_actions"]:
            validator_for("playbook_action").validate(row)
        for row in self.projected["approvals"]:
            validator_for("approval").validate(row)
            self.assertIn(row["status"], ("pending", "approved", "edited", "rejected"))

    def test_a_live_label_is_not_invented_for_a_seed_run(self) -> None:
        self.assertNotEqual(self.graph_run["served_from"], "live")
        self.assertEqual(self.projected["answer"]["served_from"], self.graph_run["served_from"])


if __name__ == "__main__":
    unittest.main()
