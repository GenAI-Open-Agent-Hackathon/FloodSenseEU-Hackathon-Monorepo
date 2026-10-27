"""ingestion/prep/ahr_hazard.py with a fake HTTP fetch: rows, units, and the rendered 045/046."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ingestion", "prep"))
import ahr_hazard as ah  # noqa: E402


def fake_fetch(url, params):
    if url == ah.FLOOD_URL:
        assert params["daily"] == "river_discharge" and params["start_date"] == "2021-07-10"
        return {"daily": {"time": ["2021-07-13", "2021-07-14", "2021-07-15"], "river_discharge": [28.04, 249.613, None]}}
    assert url == ah.ARCHIVE_URL and params["timezone"] == "GMT" and params["hourly"] == "precipitation"
    return {"hourly": {"time": ["2021-07-14T17:00", "2021-07-14T18:00", "2021-07-15T00:00"], "precipitation": [6.04, None, 0.3]}}


class AhrHazardTest(unittest.TestCase):
    def test_fetch_and_render(self):
        dis = ah.fetch_discharge(fake_fetch)
        self.assertEqual(len(dis), 2 * len(ah.AHR))  # None dropped
        self.assertEqual(dis[1], {"point_id": "AHR01", "date": "2021-07-14", "discharge_m3s": 249.61, "source": ah.SOURCE})
        hz = ah.fetch_hazard(dis, fake_fetch)
        self.assertEqual(len(hz), 2 * len(ah.AHR))
        self.assertEqual(hz[0], {"point_id": "AHR01", "ts_utc": "2021-07-14 17:00:00", "rain_mm": 6.0, "discharge_m3s": 249.61})
        self.assertIsNone(hz[1]["discharge_m3s"])  # no GloFAS value for 15 Jul in the fake
        sql = ah.render_hazard_migration(hz)
        self.assertIn("-- min_rows: 584", sql)  # 576 Valencia + 8 Ahr
        self.assertIn("('AHR01', '2021-07-15 00:00:00', 0.3D, CAST(NULL AS DOUBLE))", sql)
        self.assertIn("('VAL01', '2024-10-28 00:00:00', 3.4D, 23.38D)", sql)
        self.assertIn("-- min_rows: 144", ah.render_discharge_migration(dis))

    def test_committed_migrations_match_committed_csvs(self):
        for fname, render, src in (("045_seed_discharge_daily_ahr.sql", ah.render_discharge_migration, ah.DISCHARGE_CSV),
                                   ("046_seed_hazard_timeline_ahr.sql", ah.render_hazard_migration, ah.HAZARD_CSV)):
            with open(os.path.join(ah.MIGRATIONS, fname), encoding="utf-8") as f:
                self.assertEqual(f.read(), render(ah.read_csv(src)), fname)


if __name__ == "__main__":
    unittest.main()
