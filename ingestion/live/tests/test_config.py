"""Config and env-file tests. No network."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from floodsense_live.cli import main
from floodsense_live.config import (
    DEFAULT_STATIONS,
    Config,
    ConfigError,
    canonical_shortname,
    load_env_file,
)


class ConfigTest(unittest.TestCase):
    def test_defaults_are_the_rhine_set(self) -> None:
        config = Config.from_env({})
        self.assertEqual(config.stations, DEFAULT_STATIONS)
        self.assertIn("BONN", config.stations)
        self.assertIn("KÖLN", config.stations)
        self.assertIn("DÜSSELDORF", config.stations)
        self.assertIn("ANDERNACH", config.stations)
        self.assertEqual(config.timeseries, ("W",))
        self.assertEqual(config.interval_seconds, 900)
        self.assertEqual(config.lookback, "P1D")
        self.assertEqual(config.pg_port, 15432)
        self.assertFalse(config.all_current)

    def test_ascii_aliases_map_to_official_shortnames(self) -> None:
        self.assertEqual(canonical_shortname("KOELN"), "KÖLN")
        self.assertEqual(canonical_shortname("duesseldorf"), "DÜSSELDORF")
        config = Config.from_env({"PEGELONLINE_STATIONS": "bonn, KOELN, KOELN"})
        self.assertEqual(config.stations, ("BONN", "KÖLN"))

    def test_empty_station_list_is_rejected_unless_all_current(self) -> None:
        with self.assertRaises(ConfigError):
            Config.from_env({"PEGELONLINE_STATIONS": ""})
        config = Config.from_env(
            {"PEGELONLINE_STATIONS": "", "PEGELONLINE_ALL_CURRENT": "1"}
        )
        self.assertEqual(config.stations, ())
        self.assertTrue(config.all_current)

    def test_interval_below_a_minute_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            Config.from_env({"PEGELONLINE_INTERVAL_SECONDS": "10"})

    def test_env_file_does_not_override_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "export PEGELONLINE_LOOKBACK=PT6H",
                        "PEGELONLINE_STATIONS='BONN'",
                        "ALREADY=from-file",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            environ = {"ALREADY": "keep"}
            set_count = load_env_file(path, environ=environ)
            self.assertEqual(set_count, 2)
            self.assertEqual(environ["ALREADY"], "keep")
            self.assertEqual(environ["PEGELONLINE_LOOKBACK"], "PT6H")
            self.assertEqual(environ["PEGELONLINE_STATIONS"], "BONN")

    def test_main_rejects_an_empty_station_list_before_any_request(self) -> None:
        removed = {
            key: os.environ.pop(key)
            for key in list(os.environ)
            if key.startswith("PEGELONLINE_") or key.startswith("POSTGRES_")
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "empty.env"
                path.write_text("PEGELONLINE_STATIONS=\n", encoding="utf-8")
                code = main(["--dry-run", "--once", "--env-file", str(path)])
            self.assertEqual(code, 2)
        finally:
            os.environ.update(removed)


if __name__ == "__main__":
    unittest.main()
