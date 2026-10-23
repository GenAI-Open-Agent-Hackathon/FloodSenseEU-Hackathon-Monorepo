"""Postgres upserts for live.gauge_station and live.gauge_measurement.

psycopg is imported on first use so unit tests can import this module without
the driver installed. CI installs the pinned driver before the test step.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from floodsense_live.config import Config
from floodsense_live.models import MeasurementRow, StationRow
from floodsense_live.store import as_utc

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "001_live_gauges.sql"

STATION_UPSERT = """
INSERT INTO live.gauge_station (
    station_uuid, number, shortname, longname,
    water_shortname, water_longname,
    latitude, longitude, km, agency,
    gauge_zero_value, gauge_zero_unit, gauge_zero_valid_from,
    equidistance,
    source, source_url, licence, fetched_at
) VALUES (
    %(station_uuid)s, %(number)s, %(shortname)s, %(longname)s,
    %(water_shortname)s, %(water_longname)s,
    %(latitude)s, %(longitude)s, %(km)s, %(agency)s,
    %(gauge_zero_value)s, %(gauge_zero_unit)s, %(gauge_zero_valid_from)s,
    %(equidistance)s,
    %(source)s, %(source_url)s, %(licence)s, %(fetched_at)s
)
ON CONFLICT (station_uuid) DO UPDATE SET
    number = EXCLUDED.number,
    shortname = EXCLUDED.shortname,
    longname = EXCLUDED.longname,
    water_shortname = EXCLUDED.water_shortname,
    water_longname = EXCLUDED.water_longname,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    km = EXCLUDED.km,
    agency = EXCLUDED.agency,
    gauge_zero_value = EXCLUDED.gauge_zero_value,
    gauge_zero_unit = EXCLUDED.gauge_zero_unit,
    gauge_zero_valid_from = EXCLUDED.gauge_zero_valid_from,
    equidistance = EXCLUDED.equidistance,
    source = EXCLUDED.source,
    source_url = EXCLUDED.source_url,
    licence = EXCLUDED.licence,
    fetched_at = EXCLUDED.fetched_at
""".strip()

MEASUREMENT_UPSERT = """
INSERT INTO live.gauge_measurement (
    station_uuid, timeseries, ts_utc, value, unit,
    state_mnw_mhw, state_nsw_hsw,
    source, source_url, licence, fetched_at
) VALUES (
    %(station_uuid)s, %(timeseries)s, %(ts_utc)s, %(value)s, %(unit)s,
    %(state_mnw_mhw)s, %(state_nsw_hsw)s,
    %(source)s, %(source_url)s, %(licence)s, %(fetched_at)s
)
ON CONFLICT (station_uuid, timeseries, ts_utc) DO UPDATE SET
    value = EXCLUDED.value,
    unit = COALESCE(EXCLUDED.unit, live.gauge_measurement.unit),
    state_mnw_mhw = COALESCE(
        EXCLUDED.state_mnw_mhw, live.gauge_measurement.state_mnw_mhw
    ),
    state_nsw_hsw = COALESCE(
        EXCLUDED.state_nsw_hsw, live.gauge_measurement.state_nsw_hsw
    ),
    source = EXCLUDED.source,
    source_url = EXCLUDED.source_url,
    licence = EXCLUDED.licence,
    fetched_at = EXCLUDED.fetched_at
""".strip()

ETAG_UPSERT = """
INSERT INTO live.gauge_http_cache (cache_key, etag, fetched_at)
VALUES (%(cache_key)s, %(etag)s, %(fetched_at)s)
ON CONFLICT (cache_key) DO UPDATE SET
    etag = EXCLUDED.etag,
    fetched_at = EXCLUDED.fetched_at
""".strip()


def split_sql(text: str) -> list[str]:
    """Split a DDL file on semicolons. Full-line `--` comments are dropped."""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        kept.append(line)
    return [part.strip() for part in "\n".join(kept).split(";") if part.strip()]


def _psycopg() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "psycopg is not installed. Install ingestion/live/requirements.txt."
        ) from exc
    return psycopg


class PostgresGaugeStore:
    def __init__(self, config: Config, *, sql_path: Path | None = None) -> None:
        self.config = config
        self.sql_path = SQL_PATH if sql_path is None else sql_path

    def migrate(self) -> None:
        statements = split_sql(self.sql_path.read_text(encoding="utf-8"))
        with self._connection() as conn:
            with conn.cursor() as cur:
                for statement in statements:
                    cur.execute(statement)

    def upsert_stations(self, rows: list[StationRow]) -> int:
        if not rows:
            return 0
        payload = [_station_params(row) for row in rows]
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(STATION_UPSERT, payload)
        return len(rows)

    def upsert_measurements(self, rows: list[MeasurementRow]) -> int:
        if not rows:
            return 0
        payload = [_measurement_params(row) for row in rows]
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(MEASUREMENT_UPSERT, payload)
        return len(rows)

    def get_etag(self, cache_key: str) -> str | None:
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT etag FROM live.gauge_http_cache WHERE cache_key = %(cache_key)s",
                    {"cache_key": cache_key},
                )
                found = cur.fetchone()
        if found is None:
            return None
        return str(found[0])

    def put_etag(self, cache_key: str, etag: str, fetched_at: datetime) -> None:
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    ETAG_UPSERT,
                    {
                        "cache_key": cache_key,
                        "etag": etag,
                        "fetched_at": as_utc(fetched_at),
                    },
                )

    def station_uuid_for_shortname(self, shortname: str) -> str | None:
        """Used when a station document answers 304 and the uuid is already stored."""
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT station_uuid FROM live.gauge_station
                    WHERE upper(shortname) = upper(%(shortname)s)
                    """,
                    {"shortname": shortname},
                )
                found = cur.fetchone()
        if found is None:
            return None
        return str(found[0])

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _connect(self) -> Any:
        psycopg = _psycopg()
        return psycopg.connect(
            host=self.config.pg_host,
            port=self.config.pg_port,
            dbname=self.config.pg_db,
            user=self.config.pg_user,
            password=self.config.pg_password,
            sslmode=self.config.pg_sslmode,
            connect_timeout=10,
            application_name="floodsense_live",
        )


def _station_params(row: StationRow) -> dict[str, Any]:
    return {
        "station_uuid": row.station_uuid,
        "number": row.number,
        "shortname": row.shortname,
        "longname": row.longname,
        "water_shortname": row.water_shortname,
        "water_longname": row.water_longname,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "km": row.km,
        "agency": row.agency,
        "gauge_zero_value": row.gauge_zero_value,
        "gauge_zero_unit": row.gauge_zero_unit,
        "gauge_zero_valid_from": row.gauge_zero_valid_from,
        "equidistance": row.equidistance,
        "source": row.source,
        "source_url": row.source_url,
        "licence": row.licence,
        "fetched_at": as_utc(row.fetched_at),
    }


def _measurement_params(row: MeasurementRow) -> dict[str, Any]:
    return {
        "station_uuid": row.station_uuid,
        "timeseries": row.timeseries,
        "ts_utc": as_utc(row.ts_utc),
        "value": row.value,
        "unit": row.unit,
        "state_mnw_mhw": row.state_mnw_mhw,
        "state_nsw_hsw": row.state_nsw_hsw,
        "source": row.source,
        "source_url": row.source_url,
        "licence": row.licence,
        "fetched_at": as_utc(row.fetched_at),
    }
