"""Local data backend: contract columns, seed row counts, live pollers (no network).

The same SQL runs on SQLite here; with LOCAL_TEST_DATABASE_URL set, the contract
test also runs against a real Postgres (the CI/compose container).
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml

from floodsense_agents import localdata as L
from floodsense_agents.watch import EU_POINTS, FORECAST_POINTS

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = yaml.safe_load((ROOT / "contracts" / "views.yaml").read_text(encoding="utf-8"))["views"]
SEED_MIN = {"discharge_daily": 180, "hazard_timeline": 960, "hazard_now": 576, "gauge_levels": 3,
            "eu_watch": 11, "weather_forecast": 45, "exposure_join": 359, "provenance": 9}
PY = {"string": str, "date": str, "timestamp": str, "double": float, "int": int, "boolean": (bool, int)}
NOW = datetime(2026, 10, 29, 12, 30, tzinfo=timezone.utc)


def _om_handler(request: httpx.Request) -> httpx.Response:
    n = len(request.url.params["latitude"].split(","))
    host, q = request.url.host, request.url.params
    if host.startswith("flood-api"):
        if "past_days" in q:
            days = [(datetime(2026, 9, 29) + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(38)]
            vals = [10.0] * 30 + [10.0, 25.0, 12.0, 11.0, 10.0, 10.0, 10.0, 10.0]
        else:
            days = ["2024-10-20", "2024-10-21"]
            vals = [5.0, 6.0]
        one = {"daily": {"time": days, "river_discharge": vals}}
    elif host.startswith("archive-api"):
        one = {"hourly": {"time": ["2024-10-20T00:00", "2024-10-20T01:00"], "precipitation": [0.1, 0.2]}}
    else:
        hours = 72 if "forecast_hours" in q else 144
        base = datetime(2026, 10, 29, 12)
        times = [(base + timedelta(hours=h - (72 if hours == 144 else 0))).strftime("%Y-%m-%dT%H:%M") for h in range(hours)]
        one = {"hourly": {"time": times, "precipitation": [0.3] * hours}}
    return httpx.Response(200, json=[one] * n if n > 1 else one)


def _gauge_get(url, params=None):
    if url.endswith("measurements.json"):
        return [{"timestamp": "2026-10-29T10:00:00+00:00", "value": 100}, {"timestamp": "2026-10-29T11:00:00+00:00", "value": 110}]
    return {"shortname": "BONN", "water": {"shortname": "RHEIN"}, "km": 654.8, "latitude": 50.7, "longitude": 7.1,
            "timeseries": [{"shortname": "W", "currentMeasurement": {"timestamp": "2026-10-29T11:00:00+00:00", "value": 110},
                            "characteristicValues": [{"shortname": "MW", "unit": "cm", "value": 290},
                                                     {"shortname": "MHW", "unit": "cm", "value": 680}]}]}


class ContractTest(unittest.TestCase):
    def check(self, backend: L.LocalData, schema: str, view: str, min_rows: int | None):
        ev = backend.run_sql(f"SELECT * FROM {schema}.{view}", sample=5000)
        self.assertIsNone(ev.error, ev.error)
        self.assertEqual(ev.source, "local")
        self.assertTrue(ev.query_id.startswith("local-"))
        if min_rows is not None:
            self.assertGreaterEqual(ev.row_count, min_rows, f"{schema}.{view}")
        cols = CONTRACT[view]
        for row in ev.rows_sample:
            self.assertEqual(list(row), [c["name"] for c in cols], f"{schema}.{view} columns")
            for c in cols:
                v = row[c["name"]]
                self.assertTrue(v is None or isinstance(v, PY[c["type"]]), f"{view}.{c['name']}={v!r}")

    def test_seed_schema_sqlite(self):
        b = L.sqlite_backend(ROOT)
        for view, n in SEED_MIN.items():
            self.check(b, "floodsense_seed", view, n)

    @unittest.skipUnless(os.environ.get("LOCAL_TEST_DATABASE_URL"), "no test Postgres")
    def test_seed_schema_postgres(self):
        import psycopg

        url = os.environ["LOCAL_TEST_DATABASE_URL"]
        with psycopg.connect(url) as conn:
            L.init_db(conn, ROOT)
        b = L.LocalData(lambda: psycopg.connect(url))
        for view, n in SEED_MIN.items():
            self.check(b, "floodsense_seed", view, n)
            self.check(b, "floodsense", view, n if view in ("exposure_join", "provenance") else None)

    def test_live_refresh_with_mock_transport(self):
        conn = L.sqlite_connect()
        L.init_db(conn, ROOT)
        client = httpx.Client(transport=httpx.MockTransport(_om_handler))
        report = L.refresh(conn, client, root=ROOT, now=NOW, gauge_get=_gauge_get)
        self.assertTrue(all("failed" not in v for v in report.values()), report)
        b = L.LocalData(lambda: conn)
        L._SHARED.add(id(conn))
        self.check(b, "floodsense", "weather_forecast", len(FORECAST_POINTS) * 72)
        self.check(b, "floodsense", "eu_watch", len(EU_POINTS))
        self.check(b, "floodsense", "hazard_now", 8 * 144)
        self.check(b, "floodsense", "discharge_daily", 16)
        self.check(b, "floodsense", "hazard_timeline", 16)
        self.check(b, "floodsense", "gauge_levels", 20)
        eu = b.run_sql("SELECT band, forecast_max_m3s, past30_median_m3s FROM floodsense.eu_watch", sample=1).rows_sample[0]
        self.assertEqual((eu["band"], eu["forecast_max_m3s"], eu["past30_median_m3s"]), ("above", 25.0, 10.0))
        g = b.run_sql("SELECT level_cm, band, trend_cm_h, is_stale FROM floodsense.gauge_levels WHERE station = 'BONN'")
        self.assertEqual(g.rows_sample[0]["level_cm"], 110.0)
        self.assertEqual(g.rows_sample[0]["trend_cm_h"], 10.0)
        self.assertIn(g.rows_sample[0]["is_stale"], (True, False, 0, 1))
        past = b.run_sql("SELECT DISTINCT horizon FROM floodsense.hazard_now").rows_sample
        self.assertEqual({r["horizon"] for r in past}, {"past", "forecast"})

    def test_failed_source_leaves_rows_and_reports(self):
        conn = L.sqlite_connect()
        L.init_db(conn, ROOT)
        client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
        report = L.refresh(conn, client, root=ROOT, now=NOW, gauge_get=lambda *a, **k: (_ for _ in ()).throw(OSError("down")),
                           only=("eu_watch", "gauge_levels"))
        self.assertIn("failed", report["eu_watch"])
        self.assertIn("failed", report["gauge_levels"])
        self.assertEqual(conn.execute("SELECT count(*) FROM floodsense.eu_watch").fetchone()[0], 0)

    def test_query_id_is_stable_and_writes_refused(self):
        b = L.sqlite_backend(ROOT)
        q1 = b.run_sql("SELECT point_id FROM floodsense_seed.hazard_timeline WHERE ts_utc <= ?", ("2024-10-29T15:00:00Z",))
        q2 = b.run_sql("SELECT point_id FROM floodsense_seed.hazard_timeline WHERE ts_utc <= ?", ("2024-10-29T15:00:00Z",))
        self.assertEqual(q1.query_id, q2.query_id)
        self.assertIn("2024-10-29T15:00:00Z", q1.sql)
        with self.assertRaises(ValueError):
            b.run_sql("DELETE FROM floodsense_seed.hazard_timeline")


if __name__ == "__main__":
    unittest.main()
