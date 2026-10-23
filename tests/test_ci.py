"""The CI workflow and the gitleaks rule stay pointed at the decisions we wrote down."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.config = (ROOT / ".gitleaks.toml").read_text(encoding="utf-8")

    def test_workflow_targets_main_and_the_hosted_runner(self) -> None:
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("push:", self.workflow)
        self.assertEqual(self.workflow.count("branches: [main]"), 2)
        self.assertIn("runs-on: ubuntu-latest", self.workflow)
        self.assertIn("runs-on: [self-hosted, homelab]", self.workflow)
        self.assertIn("python tasks.py lint", self.workflow)
        self.assertIn("python tasks.py test", self.workflow)
        self.assertIn("ingestion/live/requirements.txt", self.workflow)
        self.assertIn('FLOODSENSE_REQUIRE_GITLEAKS: "1"', self.workflow)
        self.assertNotIn("uses: gitleaks/gitleaks-action", self.workflow)
        self.assertNotIn("docker://", self.workflow)
        self.assertNotIn("uses: docker", self.workflow.lower())

    def test_nvidia_rule_matches_a_long_token_and_not_the_config(self) -> None:
        block = re.search(r'id = "nvidia-api-key"(.*)', self.config, re.S)
        self.assertIsNotNone(block)
        found = re.search(r"regex = '''(.+?)'''", block.group(1) if block else "")
        self.assertIsNotNone(found)
        pattern = found.group(1) if found else ""
        self.assertIn('keywords = ["nvapi-"]', self.config)
        self.assertIn("useDefault = true", self.config)
        sample = "nvapi-" + ("a" * 20)
        self.assertRegex(sample, pattern)
        self.assertIsNone(re.search(pattern, "nvapi-short"))
        self.assertIsNone(re.search(pattern, self.config))
        self.assertIsNone(re.search(pattern, sample.swapcase()))


if __name__ == "__main__":
    unittest.main()
