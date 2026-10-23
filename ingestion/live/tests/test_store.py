"""Upsert idempotency on the in-memory store.

Postgres is not started here. GitHub Actions does not use Docker (ADR 0008),
so a test container would not run in CI. The memory store implements the same
primary keys as live.gauge_station and live.gauge_measurement, including the
COALESCE rule for unit and state columns. The SQL text is checked separately.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from floodsense_live.models import MeasurementRow, StationRow
from floodsense_live.postgres import (
    MEASUREMENT_UPSERT,
    STATION_UPSERT,
    split_sql,
)
from floodsense_live.postgres import SQL_PATH
from floodsense_live.store import InMemoryGaugeStore

FETCHED = datetime(2026, 10, 23, 16, 20, tzinfo=timezone.utc)
TS = datetime(2026, 10, 23, 16, 15, tzinfo=timezone.utc)


def _station(shortname: str = "BONN") -> StationRow:
    return StationRow(
        station_uuid="593647aa-9fea-43ec-a7d6-6476a76ae868",
        number="2710080",
        shortname=shortname,
        longname=shortname,
        water_shortname="RHEIN",
        water_longname="RHEIN",
        latitude=50.736398,
        longitude=7.108045,
        km=654.8,
        agency="STANDORT KÖLN",
        gauge_zero_value=42.713,
        gauge_zero_unit="m. ü. NHN",
        gauge_zero_valid_from="2019-11-01",
        equidistance=15,
        source="PEGELONLINE",
        source_url="https://pegelonline.wsv.de/webservices/rest-api/v2/stations/BONN.json",
        licence="DL-DE->Zero-2.0",
        fetched_at=FETCHED,
    )


def _measurement(
    *,
    value: float | None = 83.0,
    ts_utc: datetime = TS,
    state: str | None = "low",
    unit: str | None = "cm",
) -> MeasurementRow:
    return MeasurementRow(
        station_uuid="593647aa-9fea-43ec-a7d6-6476a76ae868",
        timeseries="W",
        ts_utc=ts_utc,
        value=value,
        unit=unit,
        state_mnw_mhw=state,
        state_nsw_hsw="unknown" if state is not None else None,
        source="PEGELONLINE",
        source_url="https://example.test/measurements",
        licence="DL-DE->Zero-2.0",
        fetched_at=FETCHED,
    )


class StoreTest(unittest.TestCase):
    def test_upsert_is_idempotent_for_the_same_primary_key(self) -> None:
        store = InMemoryGaugeStore()
        store.upsert_stations([_station()])
        store.upsert_stations([_station()])
        self.assertEqual(len(store.stations), 1)
        store.upsert_measurements([_measurement()])
        store.upsert_measurements([_measurement()])
        self.assertEqual(len(store.measurements), 1)
        stored = next(iter(store.measurements.values()))
        self.assertEqual(stored.value, 83.0)
        self.assertEqual(stored.licence, "DL-DE->Zero-2.0")

    def test_a_later_value_replaces_the_row_and_null_state_does_not(self) -> None:
        store = InMemoryGaugeStore()
        store.upsert_measurements([_measurement(value=83.0, state="low")])
        later = datetime(2026, 10, 23, 16, 30, tzinfo=timezone.utc)
        store.upsert_measurements(
            [_measurement(value=90.0, state=None, unit=None, ts_utc=TS)]
        )
        # fetched_at on the replacement uses the helper default FETCHED.
        # Build an explicit row so the timestamp under test stays TS.
        replacement = MeasurementRow(
            station_uuid="593647aa-9fea-43ec-a7d6-6476a76ae868",
            timeseries="W",
            ts_utc=TS,
            value=90.0,
            unit=None,
            state_mnw_mhw=None,
            state_nsw_hsw=None,
            source="PEGELONLINE",
            source_url="https://example.test/measurements",
            licence="DL-DE->Zero-2.0",
            fetched_at=later,
        )
        store.upsert_measurements([replacement])
        self.assertEqual(len(store.measurements), 1)
        stored = store.measurements[("593647aa-9fea-43ec-a7d6-6476a76ae868", "W", TS)]
        self.assertEqual(stored.value, 90.0)
        self.assertEqual(stored.unit, "cm")
        self.assertEqual(stored.state_mnw_mhw, "low")
        self.assertEqual(stored.state_nsw_hsw, "unknown")
        self.assertEqual(stored.fetched_at, later)

    def test_a_different_timestamp_inserts_another_row(self) -> None:
        store = InMemoryGaugeStore()
        other = datetime(2026, 10, 23, 16, 0, tzinfo=timezone.utc)
        store.upsert_measurements([_measurement(), _measurement(ts_utc=other, value=84.0)])
        self.assertEqual(len(store.measurements), 2)

    def test_etag_round_trip(self) -> None:
        store = InMemoryGaugeStore()
        self.assertIsNone(store.get_etag("https://example.test/a"))
        store.put_etag("https://example.test/a", '"abc"', FETCHED)
        self.assertEqual(store.get_etag("https://example.test/a"), '"abc"')

    def test_naive_timestamps_are_rejected(self) -> None:
        store = InMemoryGaugeStore()
        naive = _measurement(ts_utc=datetime(2026, 10, 23, 16, 15))
        with self.assertRaises(ValueError):
            store.upsert_measurements([naive])

    def test_postgres_sql_matches_the_memory_store_contract(self) -> None:
        ddl = SQL_PATH.read_text(encoding="utf-8")
        statements = split_sql(ddl)
        joined = "\n".join(statements)
        self.assertIn("CREATE SCHEMA IF NOT EXISTS live", joined)
        self.assertIn("CREATE TABLE IF NOT EXISTS live.gauge_station", joined)
        self.assertIn("CREATE TABLE IF NOT EXISTS live.gauge_measurement", joined)
        self.assertIn("PRIMARY KEY (station_uuid, timeseries, ts_utc)", joined)
        self.assertIn("ON CONFLICT (station_uuid) DO UPDATE", STATION_UPSERT)
        self.assertIn(
            "ON CONFLICT (station_uuid, timeseries, ts_utc) DO UPDATE",
            MEASUREMENT_UPSERT,
        )
        self.assertIn("COALESCE(EXCLUDED.unit, live.gauge_measurement.unit)", MEASUREMENT_UPSERT)
        self.assertGreaterEqual(len(statements), 4)


if __name__ == "__main__":
    unittest.main()
