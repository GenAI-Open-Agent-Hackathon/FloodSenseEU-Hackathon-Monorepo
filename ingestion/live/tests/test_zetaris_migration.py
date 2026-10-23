"""The Zetaris migration stays free of secrets and keeps the statement split."""

from __future__ import annotations

import unittest
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[3] / "zetaris" / "migrations" / "020_live_gauges.sql"
)
BONN = "593647aa-9fea-43ec-a7d6-6476a76ae868"


class ZetarisMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = MIGRATION.read_text(encoding="utf-8")

    def test_registers_jdbc_and_one_rest_table(self) -> None:
        self.assertIn("CREATE DATASOURCE floodsense_pg", self.text)
        self.assertIn(
            'REGISTER DATASOURCE TABLES ("gauge_station", "gauge_measurement")',
            self.text,
        )
        self.assertIn("CREATE LIGHTNING REST TABLE bonn_station", self.text)
        self.assertIn("CREATE OR REPLACE SCHEMASTORE VIEW pegelonline_bonn_w", self.text)
        self.assertIn("LATERAL VIEW explode(timeseries)", self.text)
        self.assertIn("CREATE SCHEMASTORE CONTAINER floodsense_live", self.text)
        self.assertIn(BONN, self.text)
        self.assertIn("includeTimeseries=true", self.text)
        self.assertIn("includeCurrentMeasurement=true", self.text)
        self.assertGreaterEqual(self.text.count("\n-- statement\n"), 8)

    def test_credentials_are_placeholders(self) -> None:
        self.assertIn('jdbcurl "${FLOODSENSE_PG_JDBC_URL}"', self.text)
        self.assertIn('username "${POSTGRES_USER}"', self.text)
        self.assertIn('password "${POSTGRES_PASSWORD}"', self.text)
        self.assertNotIn("local-dev-only", self.text)
        self.assertNotIn("nvapi-", self.text)
        self.assertNotIn("postgres://", self.text.lower())


if __name__ == "__main__":
    unittest.main()
