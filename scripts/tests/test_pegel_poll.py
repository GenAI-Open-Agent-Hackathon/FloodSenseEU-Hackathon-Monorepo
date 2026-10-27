"""ingestion/feeds/pegel_poll.py with a fake HTTP getter. No network."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingestion" / "feeds"))

import pegel_poll  # noqa: E402

STATION = {
    "shortname": "BONN", "km": 654.8, "latitude": 50.7364, "longitude": 7.108,
    "water": {"shortname": "RHEIN"},
    "timeseries": [{
        "shortname": "W", "unit": "cm",
        "currentMeasurement": {"timestamp": "2026-10-27T00:45:00+01:00", "value": 158.0},
        "characteristicValues": [
            {"shortname": "MNW", "unit": "cm", "value": 121.0},
            {"shortname": "MW", "unit": "cm", "value": 290.0},
            {"shortname": "MHW", "unit": "cm", "value": 680.0},
            {"shortname": "HHW", "unit": "cm", "value": 1013.0},
        ],
    }],
}
MEAS = [
    {"timestamp": "2026-10-26T23:30:00+01:00", "value": 150.0},
    {"timestamp": "2026-10-26T23:45:00+01:00", "value": 152.0},
    {"timestamp": "2026-10-27T00:15:00+01:00", "value": 156.0},
    {"timestamp": "2026-10-27T00:45:00+01:00", "value": 158.0},
]


def fake_get(urls: list[str]):
    def get(url, params=None):
        urls.append(url)
        if "KAPUTT" in url:
            raise OSError("boom")
        return MEAS if url.endswith("measurements.json") else STATION
    return get


class PegelPollTest(unittest.TestCase):
    def test_row_has_utc_time_trend_thresholds_and_band(self) -> None:
        row = dict(zip(pegel_poll.COLUMNS, pegel_poll.station_row("BONN", "F", fake_get([]))))
        self.assertEqual(row["ts_utc"], "2026-10-26 23:45:00")
        self.assertEqual(row["level_cm"], 158.0)
        self.assertEqual(row["trend_cm_h"], 6.0)
        self.assertEqual((row["mw_cm"], row["mhw_cm"], row["hsw_cm"]), (290.0, 680.0, None))
        self.assertEqual(row["band"], "below")
        self.assertEqual(row["source"], "ds_pegelonline")

    def test_station_names_are_url_quoted(self) -> None:
        urls: list[str] = []
        pegel_poll.station_row("KÖLN", "F", fake_get(urls))
        self.assertIn("/stations/K%C3%96LN.json", urls[0])

    def test_band(self) -> None:
        self.assertEqual(pegel_poll.band(700, 290, 680), "above")
        self.assertEqual(pegel_poll.band(600, 290, 680), "near")
        self.assertEqual(pegel_poll.band(400, 290, 680), "below")
        self.assertEqual(pegel_poll.band(None, 290, 680), "unknown")
        self.assertEqual(pegel_poll.band(400, None, None), "unknown")
        # No usable MW: MHW only, never "near".
        self.assertEqual(pegel_poll.band(670, None, 680), "below")
        self.assertEqual(pegel_poll.band(670, 700, 680), "below")
        self.assertEqual(pegel_poll.band(690, None, 680), "above")

    def test_trend_needs_two_readings(self) -> None:
        self.assertIsNone(pegel_poll.trend_cm_h(MEAS[:1]))

    def test_trend_none_when_gap_under_half_an_hour(self) -> None:
        self.assertIsNone(pegel_poll.trend_cm_h(MEAS[2:3] + [{"timestamp": "2026-10-27T00:30:00+01:00", "value": 157.0}]))

    def test_poll_writes_csv_and_skips_failed_station(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path, n, failed = pegel_poll.poll(("BONN", "KAPUTT"), fake_get([]), d)
            self.assertEqual((n, len(failed)), (1, 1))
            with open(path, newline="", encoding="utf-8") as f:
                kaputt = list(csv.DictReader(f))[1]
            self.assertEqual((kaputt["station"], kaputt["level_cm"], kaputt["band"], kaputt["fetched_at"]),
                             ("KAPUTT", "", "unknown", ""))
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(list(rows[0]), pegel_poll.COLUMNS)
            self.assertEqual(rows[0]["hsw_cm"], "")

    def test_failed_station_keeps_its_previous_row_and_old_fetched_at(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            pegel_poll.poll(("BONN",), fake_get([]), d)
            path = Path(d, "live.csv")
            old = path.read_text(encoding="utf-8").replace(",BONN,", ",X,")
            rows = list(csv.reader(old.splitlines()))
            rows[1][0] = "KAPUTT"
            rows[1][-1] = "2026-10-26 20:00:00"
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
            _, n, _ = pegel_poll.poll(("BONN", "KAPUTT"), fake_get([]), d)
            with open(path, newline="", encoding="utf-8") as f:
                kept = list(csv.DictReader(f))[1]
            self.assertEqual(n, 1)
            self.assertEqual((kept["station"], kept["level_cm"], kept["fetched_at"]),
                             ("KAPUTT", "158.0", "2026-10-26 20:00:00"))

    def test_mixed_case_name_finds_previous_upper_row(self) -> None:
        def get(url, params=None):
            raise OSError("down")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "live.csv")
            row = ["COCHEM"] + ["1"] * (len(pegel_poll.COLUMNS) - 2) + ["2026-10-26 20:00:00"]
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([pegel_poll.COLUMNS, row])
            # All fail -> file untouched; so check the row poll() would emit directly.
            prev = pegel_poll.previous_rows(str(path))
            name = "Cochem"
            self.assertNotIn(name, prev)
            self.assertEqual((prev.get(name) or prev.get(name.upper()))[-1], "2026-10-26 20:00:00")
            _, n, _ = pegel_poll.poll(("BONN", name), lambda u, p=None: fake_get([])(u, p) if "BONN" in u else get(u), d)
            with open(path, newline="", encoding="utf-8") as f:
                kept = list(csv.DictReader(f))[1]
            self.assertEqual((n, kept["station"], kept["fetched_at"]), (1, "COCHEM", "2026-10-26 20:00:00"))

    def test_050_seed_koeln_is_utf8_bytes(self) -> None:
        raw = (ROOT / "zetaris" / "migrations" / "050_seed_view_gauge_levels_utf8_koeln.sql").read_bytes()
        self.assertIn("'KÖLN'".encode("utf-8"), raw)
        self.assertIn(bytes([0x27, 0x4B, 0xC3, 0x96, 0x4C, 0x4E, 0x27]), raw)
        self.assertNotIn("Ã".encode("utf-8"), raw)

    def test_poll_keeps_last_file_when_all_fail(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            Path(d, "live.csv").write_text("old", encoding="utf-8")
            _, n, _ = pegel_poll.poll(("KAPUTT",), fake_get([]), d)
            self.assertEqual(n, 0)
            self.assertEqual(Path(d, "live.csv").read_text(encoding="utf-8"), "old")

    def test_station_list_covers_ten_federal_waterways(self) -> None:
        names = pegel_poll.STATIONS
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(names), 25)
        # The first nine are the Rhine/Mosel list this poller started with.
        for old in ("MAINZ", "KAUB", "KOBLENZ", "ANDERNACH", "BONN", "KÖLN", "DÜSSELDORF", "Trier UP", "Cochem"):
            self.assertIn(old, names)
        for name in ("DRESDEN", "PASSAU DONAU", "FRANKFURT1 (ODER)", "HANN.MUENDEN", "RHEINE UNTERSCHLEUSE"):
            self.assertIn(name, names)

    def test_names_with_brackets_and_dots_are_quoted_in_the_path(self) -> None:
        seen: list[str] = []

        def get(url, params=None):
            seen.append(url)
            raise OSError("offline")

        with tempfile.TemporaryDirectory() as d:
            pegel_poll.poll(("FRANKFURT1 (ODER)", "HANN.MUENDEN"), get, d)
        self.assertIn(f"{pegel_poll.BASE}/stations/FRANKFURT1%20%28ODER%29.json", seen)
        self.assertIn(f"{pegel_poll.BASE}/stations/HANN.MUENDEN.json", seen)

    def test_columns_match_the_live_gauge_view_header(self) -> None:
        sql = (ROOT / "zetaris" / "migrations" / "048_view_gauge_levels_is_stale.sql").read_text(encoding="utf-8")
        header = next(line for line in sql.splitlines() if line.startswith("-- columns:"))
        names = [c.strip().split()[0] for c in header.split(":", 1)[1].split(",")]
        self.assertEqual(names, pegel_poll.COLUMNS + ["is_stale"])
        self.assertIn("INTERVAL 30 MINUTES", sql)


if __name__ == "__main__":
    unittest.main()
