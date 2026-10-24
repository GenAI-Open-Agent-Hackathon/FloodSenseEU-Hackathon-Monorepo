"""The real migrations in zetaris/migrations/ keep the live and seed views in step with the contract."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import zetaris_sync as zs  # noqa: E402

VIEWS_YAML = ROOT / "contracts" / "views.yaml"


def contract_columns() -> dict[str, tuple[tuple[str, str], ...]]:
    """Column names and types per view from contracts/views.yaml. Reads the flow-style lines."""
    views: dict[str, list[tuple[str, str]]] = {}
    current = None
    for line in VIEWS_YAML.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^  ([a-z_]+):\s*$", line):
            current = match.group(1)
            views[current] = []
        elif current and (match := re.match(r"^\s*- \{name:\s*(\w+),\s*type:\s*(\w+)", line)):
            views[current].append((match.group(1), match.group(2)))
    return {name: tuple(columns) for name, columns in views.items()}


class MigrationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.migrations, problems = zs.discover(ROOT / "zetaris" / "migrations")
        assert not problems, problems
        cls.specs = {s.name: s for m in cls.migrations for s in m.views}

    def test_migrations_lint_clean(self) -> None:
        self.assertEqual(zs.lint(self.migrations), [])

    def test_every_live_view_has_a_seed_view_with_the_same_columns(self) -> None:
        live = {n.split(".", 1)[1]: s for n, s in self.specs.items() if n.startswith("floodsense.")}
        seed = {n.split(".", 1)[1]: s for n, s in self.specs.items() if n.startswith("floodsense_seed.")}
        self.assertEqual(set(live), set(seed), "each view must exist in both namespaces")
        for name in live:
            self.assertEqual(live[name].columns, seed[name].columns, name)

    @unittest.skipUnless(VIEWS_YAML.is_file(), "contracts/views.yaml is not in this checkout")
    def test_declared_views_match_contracts_views_yaml(self) -> None:
        contract = contract_columns()
        self.assertTrue(contract, "no views parsed from contracts/views.yaml")
        for full_name, spec in self.specs.items():
            name = full_name.split(".", 1)[1]
            self.assertIn(name, contract, f"{full_name} is not in contracts/views.yaml")
            self.assertEqual(spec.columns, contract[name], full_name)


if __name__ == "__main__":
    unittest.main()
