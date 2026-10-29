"""Local data backend: the same 8 contract views from Postgres, no Zetaris.

DATA_BACKEND=local selects this module (zetaris.build_zetaris). `LocalData.run_sql`
has the signature and Evidence shape of `ZetarisClient.run_sql`; only the
query id (`local-<hash of sql+params>`) and `Evidence.source` ("local") differ,
so a citation never claims Zetaris.

Data, two schemas as in the warehouse:
  floodsense_seed  frozen rows. Parsed from the VALUES lists of the Zetaris
                   migrations (012/013/050/051/052/065) and the prep CSVs, so
                   the numbers are the repo's own seed data, not new ones.
  floodsense       exposure_join and provenance (static, from the CSVs) plus
                   live tables filled by `refresh()`: PEGELONLINE gauges (via
                   ingestion/feeds/pegel_poll.py) and Open-Meteo (GloFAS flood,
                   archive rain, DWD ICON forecast). Empty until the first
                   successful pull. A failed pull leaves the old rows; nothing
                   is invented.

CLI (the compose `local-data` service): `python -m floodsense_agents.localdata run`.
Tests run the same SQL on SQLite (`sqlite_connect`) with the same loaders.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import logging
import os
import re
import sqlite3
import statistics
import sys
import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

import httpx

from floodsense_agents.models import Evidence
from floodsense_agents.settings import settings
from floodsense_agents.watch import EU_POINTS, FORECAST_POINTS
from floodsense_agents.zetaris import _view_of, check_sql, inline_bound, now_utc

log = logging.getLogger("floodsense.localdata")
BACKEND = "local"
SOURCE = "local"
UA = "FloodSenseEU-hackathon/0.1 (non-commercial)"

# (name, sql type) per view. Same names and order as contracts/views.yaml.
_COLS: dict[str, list[tuple[str, str]]] = {
    "discharge_daily": [("point_id", "TEXT"), ("date", "DATE"), ("discharge_m3s", "DOUBLE PRECISION"), ("source", "TEXT")],
    "hazard_timeline": [("point_id", "TEXT"), ("ts_utc", "TIMESTAMP"), ("rain_mm", "DOUBLE PRECISION"), ("discharge_m3s", "DOUBLE PRECISION"), ("warning_level", "TEXT")],
    "hazard_now": [("point_id", "TEXT"), ("ts_utc", "TIMESTAMP"), ("rain_mm", "DOUBLE PRECISION"), ("discharge_m3s", "DOUBLE PRECISION"), ("warning_level", "TEXT"), ("horizon", "TEXT")],
    "gauge_levels": [("station", "TEXT"), ("water", "TEXT"), ("ts_utc", "TIMESTAMP"), ("level_cm", "DOUBLE PRECISION"), ("source", "TEXT"), ("river_km", "DOUBLE PRECISION"), ("lat", "DOUBLE PRECISION"), ("lon", "DOUBLE PRECISION"), ("trend_cm_h", "DOUBLE PRECISION"), ("mnw_cm", "DOUBLE PRECISION"), ("mw_cm", "DOUBLE PRECISION"), ("mhw_cm", "DOUBLE PRECISION"), ("hhw_cm", "DOUBLE PRECISION"), ("hsw_cm", "DOUBLE PRECISION"), ("band", "TEXT"), ("fetched_at", "TIMESTAMP"), ("is_stale", "BOOLEAN")],
    "eu_watch": [("point_id", "TEXT"), ("name", "TEXT"), ("country", "TEXT"), ("river", "TEXT"), ("lat", "DOUBLE PRECISION"), ("lon", "DOUBLE PRECISION"), ("discharge_m3s", "DOUBLE PRECISION"), ("forecast_max_m3s", "DOUBLE PRECISION"), ("past30_median_m3s", "DOUBLE PRECISION"), ("band", "TEXT"), ("basis", "TEXT"), ("source", "TEXT"), ("as_of_date", "DATE")],
    "weather_forecast": [("point_id", "TEXT"), ("kind", "TEXT"), ("name", "TEXT"), ("river", "TEXT"), ("lat", "DOUBLE PRECISION"), ("lon", "DOUBLE PRECISION"), ("lead_h", "INTEGER"), ("ts_utc", "TIMESTAMP"), ("precip_mm", "DOUBLE PRECISION"), ("model", "TEXT"), ("source", "TEXT")],
    "exposure_join": [("policy_id", "TEXT"), ("site_id", "TEXT"), ("lat", "DOUBLE PRECISION"), ("lon", "DOUBLE PRECISION"), ("in_footprint", "BOOLEAN"), ("sum_insured_eur", "DOUBLE PRECISION"), ("segment", "TEXT"), ("synthetic", "TEXT")],
    "provenance": [("dataset", "TEXT"), ("source_url", "TEXT"), ("publisher", "TEXT"), ("licence", "TEXT"), ("attribution", "TEXT"), ("fetched_at", "TIMESTAMP")],
}
VIEWS = tuple(_COLS)
SCHEMAS = ("floodsense_seed", "floodsense")
_NAMES = {v: [c for c, _ in cols] for v, cols in _COLS.items()}
# floodsense.gauge_levels is a view over this table so is_stale tracks the clock (migration 048).
_PEGEL_COLS = [c for c in _NAMES["gauge_levels"] if c != "is_stale"]


# --- schema ---------------------------------------------------------------

def _stale_expr(dialect: str) -> str:
    if dialect == "sqlite":
        return "(fetched_at IS NULL OR fetched_at < datetime('now', '-30 minutes'))"
    return "(fetched_at IS NULL OR fetched_at < (now() AT TIME ZONE 'utc') - interval '30 minutes')"


def ddl(dialect: str) -> list[str]:
    """CREATE statements for both schemas. dialect: 'pg' or 'sqlite' (schemas attached by the caller)."""
    out: list[str] = []
    if dialect == "pg":
        out += [f"CREATE SCHEMA IF NOT EXISTS {s}" for s in SCHEMAS]
    for s in SCHEMAS:
        for view, cols in _COLS.items():
            if view == "gauge_levels" and s == "floodsense":
                cols = [c for c in cols if c[0] != "is_stale"]
                body = ", ".join(f"{n} {t}" for n, t in cols)
                out.append(f"CREATE TABLE IF NOT EXISTS {s}.pegel_now ({body})")
                sel = ", ".join(_PEGEL_COLS)
                out.append(f"DROP VIEW IF EXISTS {s}.gauge_levels")
                out.append(
                    f"CREATE VIEW {s}.gauge_levels AS SELECT {sel}, {_stale_expr(dialect)} AS is_stale "
                    f"FROM {s}.pegel_now"
                )
                continue
            body = ", ".join(f"{n} {t}" for n, t in cols)
            out.append(f"CREATE TABLE IF NOT EXISTS {s}.{view} ({body})")
    return out


# --- seed loaders ---------------------------------------------------------

_TOKEN = re.compile(r"'((?:[^']|'')*)'|(NULL)|(-?\d+(?:\.\d+)?)D?(?=\s*[,)])", re.I)


def _tuples(path: Path) -> list[tuple]:
    """Rows of a migration's `FROM VALUES` list: lines that start with ("'")."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("('") or s.startswith("('SELECT"):
            continue
        row = []
        for m in _TOKEN.finditer(s[1:]):
            text, null, num = m.groups()
            row.append(text.replace("''", "'") if text is not None else None if null else float(num))
        rows.append(tuple(row))
    return rows


def _csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def root_dir() -> Path:
    """Repo root, or LOCAL_SEED_DIR when the repo is mounted elsewhere (the compose service)."""
    return Path(os.environ.get("LOCAL_SEED_DIR") or Path(__file__).resolve().parents[2])


def seed_rows(root: Path | None = None) -> dict[str, list[tuple]]:
    """View -> rows for floodsense_seed, in `_NAMES` column order."""
    root = root or root_dir()
    mig = root / "zetaris" / "migrations"
    discharge = [(p, d, q, src) for p, d, q, src in _tuples(mig / "051_seed_discharge_daily_ahr.sql")]
    timeline = [(p, t, r, q, None) for p, t, r, q in _tuples(mig / "052_seed_hazard_timeline_ahr.sql")]
    gauges = []
    for st, water, ts, src, km, lat, lon, mnw, mw, mhw, hhw, hsw in _tuples(mig / "050_seed_view_gauge_levels_utf8_koeln.sql"):
        gauges.append((st, water, ts, None, src, km, lat, lon, None, mnw, mw, mhw, hhw, hsw, "unknown", None, True))
    eu = [
        (p, n, c, r, lat, lon, None, None, None, "unknown",
         "model, not an official warning: seed row, no reading", "seed:openmeteo_flood", None)
        for p, n, c, r, lat, lon in _tuples(mig / "065_seed_view_eu_watch_v2.sql")
    ]
    weather = [
        (pid, kind, name, river, lat, lon, None, None, None,
         "DWD ICON (icon_seamless) via Open-Meteo", "seed:openmeteo_forecast")
        for pid, kind, _ref, name, river, lat, lon in FORECAST_POINTS
    ]
    return {
        "discharge_daily": discharge,
        "hazard_timeline": timeline,
        # 040: the seed hazard_now is the frozen 013 window (Valencia), labelled replay.
        "hazard_now": [(p, t, r, q, w, "replay") for p, t, r, q, w in timeline if p.startswith("VAL")],
        "gauge_levels": gauges,
        "eu_watch": eu,
        "weather_forecast": weather,
        **static_rows(root),
    }


def static_rows(root: Path | None = None) -> dict[str, list[tuple]]:
    """exposure_join (018) and provenance (015/073): the same in both schemas."""
    root = root or root_dir()
    prep = root / "ingestion" / "prep"
    sites = {r["site_id"]: r for r in _csv(prep / "osm_sites.csv")}
    exposure = []
    for p in _csv(prep / "portfolio_synthetic.csv"):
        s = sites.get(p["site_id"])
        if s:  # inner join, as in the view
            exposure.append((p["policy_id"], p["site_id"], float(s["lat"]), float(s["lon"]),
                             s["in_flood_footprint"] == "yes", float(p["sum_insured_eur"]),
                             s["site_type"], p["synthetic"]))
    prov = [
        (r["dataset"], r["source_url"], r["publisher"], r["licence"], r["attribution"], r["accessed_at"])
        for r in _csv(prep / "provenance.csv") if r["dataset_id"] != "ds_dwd_brightsky"
    ]
    prov.append((
        "Open-Meteo forecast API (DWD ICON precipitation)", "https://open-meteo.com/en/docs/dwd-api",
        "Open-Meteo.com; model by Deutscher Wetterdienst (DWD)",
        "CC BY 4.0 (free API non-commercial only); DWD data CC BY 4.0",
        "Weather data by Open-Meteo.com, model DWD ICON", "2026-10-27",
    ))
    return {"exposure_join": exposure, "provenance": prov}


# --- DB plumbing ----------------------------------------------------------

def sqlite_connect() -> sqlite3.Connection:
    """In-memory SQLite with both schemas attached; the test stand-in for Postgres."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    for s in SCHEMAS:
        conn.execute(f"ATTACH DATABASE ':memory:' AS {s}")
    return conn


def _ph(conn) -> str:
    return "?" if isinstance(conn, sqlite3.Connection) else "%s"


def _dialect(conn) -> str:
    return "sqlite" if isinstance(conn, sqlite3.Connection) else "pg"


def _replace(conn, table: str, rows: list[tuple], *, where: str = "", params: tuple = ()) -> None:
    ph = _ph(conn)
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} {where}", params)
    if rows:
        cur.executemany(f"INSERT INTO {table} VALUES ({','.join([ph] * len(rows[0]))})", rows)


def init_db(conn, root: Path | None = None) -> None:
    """Create tables and load the seed. Idempotent: seed tables are replaced."""
    cur = conn.cursor()
    for stmt in ddl(_dialect(conn)):
        cur.execute(stmt)
    rows = seed_rows(root)
    for view, data in rows.items():
        _replace(conn, f"floodsense_seed.{view}", data)
    for view, data in static_rows(root).items():
        _replace(conn, f"floodsense.{view}", data)
    conn.commit()


# --- the run_sql client ---------------------------------------------------

def _norm(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


class LocalData:
    """Drop-in for the Zetaris protocol. `connect()` returns a DB-API connection."""

    backend = BACKEND

    def __init__(self, connect: Callable[[], object] | None = None) -> None:
        self._connect = connect or self._pg
        self._lock = threading.Lock()

    @staticmethod
    def _pg():
        import psycopg

        conn = psycopg.connect(settings.local_database_url, connect_timeout=10)
        conn.read_only = True  # the agents may only read
        return conn

    @staticmethod
    def query_id(sql: str, params: tuple[str, ...] | None) -> str:
        h = hashlib.sha256(("\x1f".join((sql, *(params or ())))).encode()).hexdigest()[:16]
        return f"local-{h}"

    def run_sql(self, sql: str, params: tuple[str, ...] | None = None, sample: int = 20) -> Evidence:
        placeholder = check_sql(sql)  # a write is refused as an exception, like the other clients
        qid = self.query_id(placeholder, params)
        try:
            rendered, bound = inline_bound(placeholder, params)
            check_sql(rendered)
            conn = self._connect()
            try:
                text = placeholder
                if not isinstance(conn, sqlite3.Connection):
                    text = placeholder.replace("%", "%%").replace("?", "%s")
                cur = conn.cursor()
                cur.execute(text, bound)
                names = [d[0] for d in cur.description]
                rows = [dict(zip(names, map(_norm, r))) for r in cur.fetchall()]
            finally:
                if not _is_shared(conn):
                    conn.close()
            return Evidence(query_id=qid, view=_view_of(rendered), sql=rendered, rows_sample=rows[:sample],
                            row_count=len(rows), executed_at_utc=now_utc(), source=SOURCE)
        except Exception as e:  # a failed read is evidence of a failed read, as in ZetarisClient
            log.warning("local query failed: %s", str(e)[:200])
            return Evidence(query_id=qid, view=_view_of(sql), sql=sql, rows_sample=[], row_count=0,
                            executed_at_utc=now_utc(), source=SOURCE, error=str(e)[:300])


_SHARED: set[int] = set()


def _is_shared(conn) -> bool:
    return id(conn) in _SHARED


def sqlite_backend(root: Path | None = None) -> LocalData:
    """LocalData over a seeded in-memory SQLite (tests, contract check)."""
    conn = sqlite_connect()
    init_db(conn, root)
    _SHARED.add(id(conn))
    return LocalData(lambda: conn)


# --- live pollers ---------------------------------------------------------

_FLOOD = "https://flood-api.open-meteo.com/v1/flood"
_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
_FORECAST = "https://api.open-meteo.com/v1/forecast"
_VAL = [p for p in FORECAST_POINTS if p[1] == "valencia"]


def _om(client: httpx.Client, url: str, pts, **params) -> list[dict]:
    """One Open-Meteo call for several places; always a list, in request order."""
    q = {"latitude": ",".join(str(p[-2]) for p in pts), "longitude": ",".join(str(p[-1]) for p in pts),
         "timezone": "GMT", **params}
    r = client.get(url, params=q, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    js = r.json()
    return js if isinstance(js, list) else [js]


def _stamp(t: str) -> str:
    return t.replace("T", " ") + (":00" if len(t) == 16 else "")


def fetch_weather_forecast(client: httpx.Client, now: datetime) -> list[tuple]:
    """070/071: DWD ICON hourly precipitation, 72 h from the current GMT hour, 45 places."""
    out = []
    for p, js in zip(FORECAST_POINTS, _om(client, _FORECAST, FORECAST_POINTS, hourly="precipitation",
                                          models="icon_seamless", forecast_hours=72)):
        times, mm = js["hourly"]["time"], js["hourly"]["precipitation"]
        for h, (t, v) in enumerate(zip(times, mm)):
            out.append((p[0], p[1], p[3], p[4], p[5], p[6], h, _stamp(t), v,
                        "DWD ICON (icon_seamless) via Open-Meteo", "Open-Meteo forecast API (DWD ICON)"))
    return out


def fetch_eu_watch(client: httpx.Client, now: datetime) -> list[tuple]:
    """063/064: GloFAS past 30 + 7 forecast days; band vs 2x the exact past-30-day median."""
    today = now.date().isoformat()
    out = []
    for (pid, name, cc, river, lat, lon), js in zip(
        EU_POINTS, _om(client, _FLOOD, [(p[4], p[5]) for p in EU_POINTS], daily="river_discharge",
                       past_days=30, forecast_days=7)):
        series = [(d, q) for d, q in zip(js["daily"]["time"], js["daily"]["river_discharge"]) if q is not None]
        past = [q for d, q in series if d < today]
        fut = [q for d, q in series if d >= today]
        cur = next((q for d, q in series if d == today), None)
        fmax = max(fut) if fut else None
        med = statistics.median(past) if past else None
        if fmax is None or med is None or med <= 0:
            band = "unknown"
        else:
            band = "above" if fmax >= 2 * med else "near" if fmax >= 1.5 * med else "below"
        out.append((pid, name, cc, river, lat, lon, cur, fmax, med, band,
                    "model, not an official warning: GloFAS 7-day forecast max vs 2x past-30-day median",
                    "Open-Meteo Flood API (GloFAS)", today))
    return out


def fetch_hazard_now(client: httpx.Client, now: datetime) -> list[tuple]:
    """030/032/042: 3 past + 3 forecast days of hourly rain, GloFAS daily discharge, 8 Valencia points."""
    rain = _om(client, _FORECAST, _VAL, hourly="precipitation", past_days=3, forecast_days=3)
    flow = _om(client, _FLOOD, _VAL, daily="river_discharge", past_days=7, forecast_days=7)
    cutoff = now.strftime("%Y-%m-%d %H:%M:%S")
    out = []
    for p, r, f in zip(_VAL, rain, flow):
        q = dict(zip(f["daily"]["time"], f["daily"]["river_discharge"]))
        for t, mm in zip(r["hourly"]["time"], r["hourly"]["precipitation"]):
            ts = _stamp(t)
            out.append((p[0], ts, mm, q.get(t[:10]), None, "forecast" if ts > cutoff else "past"))
    return out


def fetch_valencia_window(client: httpx.Client) -> tuple[list[tuple], list[tuple]]:
    """003/006: the fixed 2024-10-20 .. 2024-11-05 window around EMSR773 (discharge_daily, hazard_timeline)."""
    win = {"start_date": "2024-10-20", "end_date": "2024-11-05"}
    flow = _om(client, _FLOOD, _VAL, daily="river_discharge", **win)
    rain = _om(client, _ARCHIVE, _VAL, hourly="precipitation", **win)
    daily, timeline = [], []
    for p, f, r in zip(_VAL, flow, rain):
        q = dict(zip(f["daily"]["time"], f["daily"]["river_discharge"]))
        daily += [(p[0], d, v, "open-meteo-flood-glofas") for d, v in q.items()]
        timeline += [(p[0], _stamp(t), mm, q.get(t[:10]), None)
                     for t, mm in zip(r["hourly"]["time"], r["hourly"]["precipitation"])]
    return daily, timeline


def _load_pegel_poll(root: Path):
    path = root / "ingestion" / "feeds" / "pegel_poll.py"
    spec = importlib.util.spec_from_file_location("pegel_poll", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pegel_poll"] = mod
    spec.loader.exec_module(mod)
    return mod


def fetch_gauges(root: Path | None = None, get=None, now: datetime | None = None) -> list[tuple]:
    """PEGELONLINE current water level for the 26 stations, via ingestion/feeds/pegel_poll.py."""
    pp = _load_pegel_poll(root or root_dir())
    fetched = pp.stamp(now or datetime.now(timezone.utc))
    out = []
    for name in pp.STATIONS:
        try:
            row = pp.station_row(name, fetched, get=get or pp.fetch_json)
        except Exception as e:  # one station down must not drop the others
            log.warning("pegel %s failed: %s", name, str(e)[:120])
            continue
        out.append(tuple(row[:2]) + (row[2] or None,) + tuple(row[3:]))
    return out


def refresh(conn, client: httpx.Client | None = None, *, root: Path | None = None, now: datetime | None = None,
            gauge_get=None, only: tuple[str, ...] | None = None) -> dict[str, str]:
    """Pull every live source into `floodsense.*`. Returns table -> 'n rows' or the error text."""
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    own = client is None
    client = client or httpx.Client(follow_redirects=True)
    report: dict[str, str] = {}
    jobs: dict[str, Callable[[], None]] = {}

    def put(table: str, rows: list[tuple]) -> None:
        if not rows:
            raise RuntimeError("source returned no rows")
        _replace(conn, f"floodsense.{table}", rows)
        conn.commit()
        report[table] = f"{len(rows)} rows"

    def gauges() -> None:
        rows = fetch_gauges(root, gauge_get, now)
        if not rows:
            raise RuntimeError("no station answered")
        _replace(conn, "floodsense.pegel_now", rows)  # whole set; a failed station keeps no stale row
        conn.commit()
        report["gauge_levels"] = f"{len(rows)} rows"

    jobs["gauge_levels"] = gauges
    jobs["weather_forecast"] = lambda: put("weather_forecast", fetch_weather_forecast(client, now))
    jobs["eu_watch"] = lambda: put("eu_watch", fetch_eu_watch(client, now))
    jobs["hazard_now"] = lambda: put("hazard_now", fetch_hazard_now(client, now))

    def window() -> None:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM floodsense.discharge_daily")
        if cur.fetchone()[0]:
            report["discharge_daily"] = "kept (fixed window)"
            return
        daily, timeline = fetch_valencia_window(client)
        put("discharge_daily", daily)
        put("hazard_timeline", timeline)

    jobs["discharge_daily"] = window
    try:
        for name, job in jobs.items():
            if only and name not in only:
                continue
            try:
                job()
            except Exception as e:
                report[name] = f"failed: {str(e)[:160]}"
                log.warning("refresh %s failed: %s", name, report[name])
    finally:
        if own:
            client.close()
    return report


def main(argv: list[str] | None = None) -> int:
    """`init` loads the seed; `run` is init, then refresh every LOCAL_REFRESH_S (default 600 s)."""
    import psycopg

    cmd = (argv or sys.argv[1:] or ["run"])[0]
    interval = int(os.environ.get("LOCAL_REFRESH_S", "600"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for attempt in range(30):  # Postgres may still be starting
        try:
            conn = psycopg.connect(settings.local_database_url, connect_timeout=5)
            break
        except psycopg.OperationalError as e:
            log.info("waiting for Postgres: %s", str(e)[:100])
            time.sleep(2)
    else:
        return 1
    init_db(conn)
    log.info("seed loaded into floodsense_seed")
    if cmd == "init":
        return 0
    last_om = 0.0
    while True:
        # Open-Meteo is polled at most every 30 min; PEGELONLINE every cycle.
        only = None if time.time() - last_om > 1800 else ("gauge_levels",)
        if only is None:
            last_om = time.time()
        log.info("refresh: %s", refresh(conn, only=only))
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
