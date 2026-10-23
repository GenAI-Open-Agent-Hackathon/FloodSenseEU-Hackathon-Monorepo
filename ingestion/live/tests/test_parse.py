"""Parser tests against recorded PEGELONLINE bodies. No network."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from floodsense_live.parse import ParseError, parse_measurements, parse_station, parse_timestamp

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ParseTest(unittest.TestCase):
    def test_bonn_station_keeps_water_level_and_converts_to_utc(self) -> None:
        station, currents = parse_station(_load("bonn_station.json"), timeseries=("W",))
        self.assertEqual(station.uuid, "593647aa-9fea-43ec-a7d6-6476a76ae868")
        self.assertEqual(station.shortname, "BONN")
        self.assertEqual(station.water_shortname, "RHEIN")
        self.assertEqual(station.agency, "STANDORT KÖLN")
        self.assertEqual(station.km, 654.8)
        self.assertEqual(station.equidistance, 15)
        self.assertEqual(station.gauge_zero_value, 42.713)
        self.assertEqual(station.gauge_zero_unit, "m. ü. NHN")
        self.assertEqual(station.gauge_zero_valid_from, "2019-11-01")
        self.assertEqual(len(currents), 1)
        current = currents[0]
        self.assertEqual(current.timeseries, "W")
        self.assertEqual(current.unit, "cm")
        self.assertEqual(current.value, 83.0)
        self.assertEqual(current.state_mnw_mhw, "low")
        self.assertEqual(current.state_nsw_hsw, "unknown")
        self.assertEqual(
            current.ts_utc,
            datetime(2026, 10, 23, 16, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(current.ts_utc.tzinfo, timezone.utc)

    def test_discharge_series_is_not_stored_when_only_w_is_configured(self) -> None:
        _station, currents = parse_station(_load("bonn_station.json"), timeseries=("W",))
        self.assertTrue(all(item.timeseries == "W" for item in currents))

    def test_measurement_list_normalises_each_offset(self) -> None:
        rows = parse_measurements(
            _load("bonn_w_measurements.json"),
            station_uuid="593647aa-9fea-43ec-a7d6-6476a76ae868",
            timeseries="W",
            unit="cm",
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].ts_utc, datetime(2026, 10, 23, 15, 45, tzinfo=timezone.utc))
        self.assertEqual(rows[1].ts_utc, datetime(2026, 10, 23, 16, 0, tzinfo=timezone.utc))
        self.assertEqual(rows[1].value, 84.0)
        self.assertIsNone(rows[1].state_mnw_mhw)
        self.assertEqual(rows[2].ts_utc, datetime(2026, 10, 23, 16, 15, tzinfo=timezone.utc))

    def test_zulu_and_naive_timestamps(self) -> None:
        self.assertEqual(
            parse_timestamp("2026-10-23T16:15:00Z"),
            datetime(2026, 10, 23, 16, 15, tzinfo=timezone.utc),
        )
        with self.assertRaises(ParseError):
            parse_timestamp("2026-10-23T18:15:00")

    def test_missing_value_is_stored_as_null(self) -> None:
        payload = [{"timestamp": "2026-10-23T18:15:00+02:00"}]
        rows = parse_measurements(
            payload,
            station_uuid="u",
            timeseries="W",
            unit=None,
        )
        self.assertIsNone(rows[0].value)

    def test_measurements_must_be_an_array(self) -> None:
        with self.assertRaises(ParseError):
            parse_measurements({}, station_uuid="u", timeseries="W", unit="cm")


if __name__ == "__main__":
    unittest.main()
