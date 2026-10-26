"""036 re-registers FILESTORE tables. Gauge and hazard_now headers stay with the contract."""

from __future__ import annotations

import csv
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))

from floodsense_agents.events import EVENTS  # noqa: E402

MIGRATIONS = ROOT / "zetaris" / "migrations"


def text(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8")


def sql_body(name: str) -> str:
    return "\n".join(
        line for line in text(name).splitlines() if not line.strip().startswith("--")
    )


def sql_stamp(utc: str) -> str:
    """events.py instants, in the timestamp form the seed view stores."""
    if utc.endswith("Z"):
        utc = utc[:-1]
    return utc.replace("T", " ")


class LiveGaugeMigrationTest(unittest.TestCase):
    def test_036_reregisters_new_names_on_the_033_paths_and_does_not_drop(self) -> None:
        old = text("033_live_feed_tables.sql")
        new = text("036_reregister_live_filestore.sql")
        body = sql_body("036_reregister_live_filestore.sql")
        old_paths = re.findall(r'path "([^"]+)"', old)
        new_paths = re.findall(r'path "([^"]+)"', new)
        self.assertEqual(old_paths, new_paths)
        self.assertGreaterEqual(len(new_paths), 5)
        self.assertNotIn("-- view:", new)
        # The comment may name DROP to say the engine refused it. The statements do not.
        self.assertIsNone(re.search(r"(?i)\bdrop\b", body))
        for path in new_paths:
            table = path.rstrip("/").rsplit("/", 1)[-1]
            self.assertNotRegex(new, rf"FILESTORE TABLE {table} FROM")
            self.assertIn(f"FILESTORE TABLE {table}_staged FROM", new)
        self.assertIn("pegel_levels_staged", new)
        self.assertNotIn("dwd_rain_hourly", new)

    def test_gauge_views_declare_the_contract_headers(self) -> None:
        columns = "station string, water string, ts_utc timestamp, level_cm double, source string"
        live = text("037_create_view_gauge_levels.sql")
        seed = text("038_create_seed_view_gauge_levels.sql")
        self.assertIn("-- view: floodsense.gauge_levels", live)
        self.assertIn("-- view: floodsense_seed.gauge_levels", seed)
        self.assertIn(f"-- columns: {columns}", live)
        self.assertIn(f"-- columns: {columns}", seed)
        self.assertIn("-- min_rows: 0", live)
        self.assertIn("-- min_rows: 6", seed)
        later = text("043_seed_gauge_levels_ahr.sql")
        self.assertIn(f"-- columns: {columns}", later)
        self.assertIn("-- view: floodsense_seed.gauge_levels", later)
        gauge_rows = [
            (event.event_id, station, water)
            for event in EVENTS.values()
            for station, water in event.gauges
        ]
        self.assertEqual(len(gauge_rows), 3)
        self.assertEqual([row[0] for row in gauge_rows], ["EMSR517", "EMSR517", "EMSR517"])
        self.assertIn("-- min_rows: 3", later)
        self.assertIn("pegel_levels_staged", sql_body("037_create_view_gauge_levels.sql"))
        self.assertIn("Quelle: WSV, PEGELONLINE", live)
        body = sql_body("043_seed_gauge_levels_ahr.sql")
        self.assertIn("seed:pegelonline", body)
        self.assertIn("CAST(NULL AS DOUBLE)", body)
        for event in EVENTS.values():
            stamp = sql_stamp(event.window_from_utc)
            if event.gauges:
                self.assertIn(stamp, body)
            else:
                self.assertNotIn(stamp, body)
        for _event_id, station, water in gauge_rows:
            self.assertIn(station, body)
            self.assertIn(water, body)

    def test_hazard_now_labels_the_rolling_window_and_the_seed_does_not_invent_one(self) -> None:
        live = sql_body("042_label_hazard_now_past.sql")
        live_file = text("042_label_hazard_now_past.sql")
        seed_sql = sql_body("040_label_seed_hazard_now_horizon.sql")
        seed_file = text("040_label_seed_hazard_now_horizon.sql")
        columns = (
            "point_id string, ts_utc timestamp, rain_mm double, discharge_m3s double, "
            "warning_level string, horizon string"
        )
        self.assertIn(f"-- columns: {columns}", live_file)
        self.assertIn(f"-- columns: {columns}", seed_file)
        self.assertIn("-- min_rows: 1152", live_file)
        self.assertIn("-- min_rows: 576", seed_file)
        self.assertIn("'forecast'", live)
        self.assertIn("'past'", live)
        self.assertNotIn("observed", live_file)
        self.assertIn("current_timestamp()", live)
        self.assertIn("'replay'", seed_sql)
        self.assertNotIn("current_timestamp", seed_sql)
        self.assertIn("floodsense_seed.hazard_timeline", seed_sql)
        self.assertIn("013", seed_file)
        self.assertIn("invent", seed_file.lower())
        # 034 and 035 stay the merged files. The labels arrive as later migrations.
        self.assertNotIn("horizon", text("034_create_view_hazard_now.sql"))
        self.assertNotIn("horizon", text("035_create_seed_view_hazard_now.sql"))

    def test_forecast_provenance_row_matches_the_other_open_meteo_rows(self) -> None:
        with (ROOT / "ingestion" / "prep" / "provenance.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        by_id = {row["dataset_id"]: row for row in rows}
        self.assertIn("ds_open_meteo_forecast", by_id)
        forecast = by_id["ds_open_meteo_forecast"]
        rain = by_id["ds_open_meteo_rain"]
        self.assertEqual(forecast["publisher"], rain["publisher"])
        self.assertEqual(forecast["licence"], rain["licence"])
        self.assertEqual(forecast["attribution"], rain["attribution"])
        self.assertIn("hazard_now", forecast["dataset"])
        self.assertEqual(
            forecast["notes"],
            "REST tables rain_live (032) and glofas_discharge_live (030). "
            "hazard_now.horizon is past or forecast against the query clock. "
            "past is Open-Meteo past_days plus GloFAS model output, not a station measurement. "
            "Not a stored copy",
        )
        self.assertIn("observed event", by_id["ds_ems_emsr773"]["dataset"])
        self.assertIn("Quelle: WSV, PEGELONLINE", by_id["ds_pegelonline"]["attribution"])
        cleared = [row for row in rows if row["dataset_id"] != "ds_dwd_brightsky"]
        self.assertEqual(len(cleared), 8)
        prov = text("041_provenance_forecast_source.sql")
        self.assertEqual(prov.count("-- min_rows: 8"), 2)
        self.assertEqual(prov.count("dataset_id <> 'ds_dwd_brightsky'"), 2)
        self.assertIn("ds_open_meteo_forecast", prov)
        sources = (ROOT / "docs" / "legal" / "sources.md").read_text(encoding="utf-8")
        self.assertIn("floodsense.gauge_levels", sources)
        self.assertIn("Quelle: WSV, PEGELONLINE", sources)
        readme = (ROOT / "ingestion" / "prep" / "README.md").read_text(encoding="utf-8")
        self.assertIn("Stage before any FILESTORE registration", readme)
        self.assertIn("036", readme)
        self.assertIn("docker cp", readme)
        self.assertIn("skip-if-present", readme)
        self.assertNotIn("does not overwrite", readme)
        self.assertNotIn("labelled `observed`", sources)
        self.assertIn("`past`", sources)


if __name__ == "__main__":
    unittest.main()
