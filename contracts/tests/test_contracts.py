"""Example payloads match the JSON Schema and the Pydantic mirrors."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticError

CONTRACTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTRACTS / "python"))

from floodsense_contracts.models import (  # noqa: E402
    Answer,
    Approval,
    Citation,
    Claim,
    Evidence,
    Judge,
    JudgeClaim,
    Locator,
    PlaybookAction,
)

SCHEMA = json.loads((CONTRACTS / "schemas" / "floodsense.schema.json").read_text(encoding="utf-8"))
DEFS = SCHEMA["$defs"]

# Schema $def -> Pydantic model. answer itself is an allOf of these pieces.
MODELS = {
    "locator": Locator,
    "citation": Citation,
    "evidence": Evidence,
    "claim": Claim,
    "judge_claim": JudgeClaim,
    "judge": Judge,
    "playbook_action": PlaybookAction,
    "approval": Approval,
    "answer_fields": Answer,
}

EXAMPLES = {
    "claim": ("claim.json", Claim),
    "evidence": ("evidence.json", Evidence),
    "citation": ("citation.json", Citation),
    "judge": ("judge.json", Judge),
    "playbook_action": ("playbook_action.json", PlaybookAction),
    "approval": ("approval.json", Approval),
    "answer": ("answer_live.json", Answer),
}


def example(name: str) -> dict:
    path = CONTRACTS / "examples" / name
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(def_name: str) -> Draft202012Validator:
    wrapper = {
        "$schema": SCHEMA["$schema"],
        "$defs": DEFS,
        "$ref": f"#/$defs/{def_name}",
    }
    return Draft202012Validator(
        wrapper,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def assert_invalid(testcase: unittest.TestCase, def_name: str, payload: dict) -> None:
    with testcase.assertRaises(ValidationError):
        validator_for(def_name).validate(payload)


class ContractTests(unittest.TestCase):
    def test_schema_is_draft_2020_12(self) -> None:
        self.assertEqual(
            SCHEMA["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_examples_match_schema_and_models(self) -> None:
        for def_name, (filename, model) in EXAMPLES.items():
            payload = example(filename)
            validator_for(def_name).validate(payload)
            parsed = model.model_validate(payload)
            again = parsed.model_dump(mode="json", exclude_none=True)
            validator_for(def_name).validate(again)

        replay = example("answer_replay.json")
        validator_for("answer").validate(replay)
        dumped = Answer.model_validate(replay).model_dump(mode="json", exclude_none=True)
        validator_for("answer").validate(dumped)

    def test_answer_embeds_the_shared_examples(self) -> None:
        live = example("answer_live.json")
        replay = example("answer_replay.json")
        self.assertEqual(live["claims"][0], example("claim.json"))
        self.assertEqual(live["citations"][0], example("citation.json"))
        self.assertEqual(live["evidence"][0], example("evidence.json"))
        self.assertEqual(replay["claims"][0], example("claim.json"))
        self.assertEqual(replay["playbook_actions"][0], example("playbook_action.json"))
        self.assertEqual(replay["judge"], example("judge.json"))
        self.assertEqual(example("approval.json")["judge"], example("judge.json"))

    def test_quote_hash_matches_the_citation(self) -> None:
        citation = example("citation.json")
        digest = hashlib.sha256(citation["quote"].encode()).hexdigest()
        self.assertEqual(citation["content_sha256"], digest)

    def test_replay_links_claims_citations_and_actions(self) -> None:
        answer = example("answer_replay.json")
        claim_ids = {claim["claim_id"] for claim in answer["claims"]}
        citation_ids = {citation["citation_id"] for citation in answer["citations"]}
        query_ids = {row["query_id"] for row in answer["evidence"]}
        for citation in answer["citations"]:
            self.assertIn(citation["claim_id"], claim_ids)
            if "query_id" in citation:
                self.assertIn(citation["query_id"], query_ids)
        for action in answer["playbook_actions"]:
            self.assertEqual(action["run_id"], answer["run_id"])
            for citation_id in action["citation_ids"]:
                self.assertIn(citation_id, citation_ids)
        for scored in answer["judge"]["claims"]:
            self.assertIn(scored["claim_id"], claim_ids)

    def test_model_fields_match_schema_properties(self) -> None:
        for def_name, model in MODELS.items():
            spec = DEFS[def_name]
            self.assertFalse(spec.get("additionalProperties", True), def_name)
            properties = set(spec["properties"])
            self.assertEqual(set(model.model_fields), properties, def_name)
            required = set(spec.get("required", []))
            model_required = {
                name for name, field in model.model_fields.items() if field.is_required()
            }
            self.assertEqual(model_required, required, def_name)

    def test_typescript_names_every_wire_field(self) -> None:
        text = (CONTRACTS / "typescript" / "index.ts").read_text(encoding="utf-8")
        for def_name, spec in DEFS.items():
            if "properties" not in spec:
                continue
            for prop in spec["properties"]:
                self.assertRegex(text, rf"\b{re.escape(prop)}\b", f"{def_name}.{prop}")

    def test_rejects_bad_payloads(self) -> None:
        citation = example("citation.json")
        missing = dict(citation)
        del missing["claim_id"]
        assert_invalid(self, "citation", missing)

        evidence = example("evidence.json")
        too_many = deepcopy(evidence)
        too_many["rows_sample"] = [{"site_id": "example"} for _ in range(21)]
        assert_invalid(self, "evidence", too_many)
        with self.assertRaises(PydanticError):
            Evidence.model_validate(too_many)

        judge = example("judge.json")
        contradicted = deepcopy(judge)
        contradicted["claims"][0]["grounding"] = "contradicted"
        assert_invalid(self, "judge", contradicted)

        live = example("answer_live.json")
        labelled_live = dict(live)
        labelled_live["cached_at"] = "2026-10-22T14:32:00Z"
        assert_invalid(self, "answer", labelled_live)
        with self.assertRaises(PydanticError):
            Answer.model_validate(labelled_live)

        replay = example("answer_replay.json")
        unlabelled = dict(replay)
        unlabelled["cached_at"] = None
        assert_invalid(self, "answer", unlabelled)
        with self.assertRaises(PydanticError):
            Answer.model_validate(unlabelled)

        auto = deepcopy(judge)
        auto["claims"][0]["model_id"] = "meterless/auto"
        assert_invalid(self, "judge", auto)

        bad_time = deepcopy(evidence)
        bad_time["executed_at_utc"] = "not-a-date"
        assert_invalid(self, "evidence", bad_time)
        with self.assertRaises(PydanticError):
            Evidence.model_validate(bad_time)

        bad_url = dict(citation)
        bad_url["source_url"] = "not a url"
        assert_invalid(self, "citation", bad_url)

    def test_pinned_lanes_are_the_gameplan_ids(self) -> None:
        self.assertEqual(
            DEFS["judge_claim"]["properties"]["model_id"]["enum"],
            [
                "nvidia/nemotron-3.5-lightning-30b-a3b",
                "nvidia/nemotron-3-super-120b-a12b",
            ],
        )
        self.assertEqual(
            DEFS["answer_fields"]["properties"]["served_from"]["enum"],
            ["live", "cache", "replay"],
        )


if __name__ == "__main__":
    unittest.main()
