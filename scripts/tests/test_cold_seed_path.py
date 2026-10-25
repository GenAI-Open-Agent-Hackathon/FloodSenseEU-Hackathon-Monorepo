"""Cold seed path: DWD stays opt-in, and 033 placeholders do not include it."""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ColdSeedPathTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.feeds = load(ROOT / "ingestion" / "feeds" / "feeds.py", "floodsense_feeds")
        cls.stage = load(ROOT / "ingestion" / "prep" / "stage_local_zetaris.py", "stage_local_zetaris")

    def test_default_pull_excludes_dwd_and_only_opts_in(self) -> None:
        default = self.feeds.selected_sources(None)
        self.assertNotIn("dwd", default)
        self.assertIn("dwd", self.feeds.SOURCES)
        self.assertIn("aemet", default)
        self.assertIn("pegelonline", default)
        self.assertEqual(self.feeds.selected_sources("dwd"), ["dwd"])
        self.assertEqual(self.feeds.selected_sources("aemet,dwd"), ["aemet", "dwd"])
        with self.assertRaises(ValueError):
            self.feeds.selected_sources("not-a-source")

    def test_live_placeholders_and_migration_033_omit_dwd(self) -> None:
        self.assertNotIn("dwd_rain_hourly", self.stage.LIVE_HEADERS)
        self.assertIn("aemet_daily", self.stage.LIVE_HEADERS)
        sql = (ROOT / "zetaris" / "migrations" / "033_live_feed_tables.sql").read_text(encoding="utf-8")
        self.assertNotIn("FILESTORE TABLE dwd_rain_hourly", sql)
        for table in self.stage.LIVE_HEADERS:
            self.assertIn(table, sql)

    def test_default_stage_skips_a_held_dwd_directory(self) -> None:
        held = self.feeds.held_stage_dirs()
        self.assertIn("dwd", held)
        self.assertIn("dwd_rain_hourly", held)
        kept = self.feeds.stageable_tables(
            ["discharge_daily", "dwd_rain_hourly", "dwd", "aemet_daily"]
        )
        self.assertEqual(kept, ["discharge_daily", "aemet_daily"])

    def test_provenance_views_drop_the_held_dwd_row(self) -> None:
        where = "WHERE dataset_id <> 'ds_dwd_brightsky'"
        for name in (
            "015_create_view_provenance.sql",
            "017_create_seed_view_provenance.sql",
        ):
            text = (ROOT / "zetaris" / "migrations" / name).read_text(encoding="utf-8")
            sql = "\n".join(
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("--")
            )
            self.assertIn(where, sql)
            self.assertNotIn(where, "\n".join(
                line for line in text.splitlines() if line.strip().startswith("--")
            ))
            self.assertIn("-- min_rows: 7", text)
        exposure = (ROOT / "zetaris" / "migrations" / "018_label_exposure_synthetic.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("p.synthetic AS synthetic", exposure)
        self.assertIn("floodsense_seed", exposure)
        self.assertIn("-- min_rows: 136", (ROOT / "zetaris" / "migrations" / "004_create_view_discharge_daily.sql").read_text(encoding="utf-8"))
        self.assertIn("-- min_rows: 136", (ROOT / "zetaris" / "migrations" / "012_create_seed_view_discharge_daily.sql").read_text(encoding="utf-8"))

    def test_osm_live_pull_can_target_another_csv(self) -> None:
        sites = load(ROOT / "ingestion" / "prep" / "osm_sites.py", "osm_sites_for_test")
        previous = os.environ.get("FLOODSENSE_OSM_SITES_OUT")
        os.environ["FLOODSENSE_OSM_SITES_OUT"] = "/tmp/floodsense-live-osm.csv"
        try:
            self.assertEqual(sites.output_path(), "/tmp/floodsense-live-osm.csv")
        finally:
            if previous is None:
                os.environ.pop("FLOODSENSE_OSM_SITES_OUT", None)
            else:
                os.environ["FLOODSENSE_OSM_SITES_OUT"] = previous
            self.assertTrue(sites.output_path().endswith("osm_sites.csv"))


if __name__ == "__main__":
    unittest.main()
