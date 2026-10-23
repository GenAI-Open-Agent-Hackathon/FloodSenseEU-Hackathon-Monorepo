"""Gauge store. The in-memory store is the CI stand-in for Postgres.

CI does not run Docker (ADR 0008), so tests do not start a Postgres container.
`InMemoryGaugeStore` implements the same primary keys and the same rule for
nullable state and unit columns: a later row does not erase a value with NULL.
`PostgresGaugeStore` is the process that talks to the compose database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from floodsense_live.models import MeasurementRow, StationRow


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


class GaugeStore(Protocol):
    def migrate(self) -> None: ...

    def upsert_stations(self, rows: list[StationRow]) -> int: ...

    def upsert_measurements(self, rows: list[MeasurementRow]) -> int: ...

    def get_etag(self, cache_key: str) -> str | None: ...

    def put_etag(self, cache_key: str, etag: str, fetched_at: datetime) -> None: ...


class InMemoryGaugeStore:
    """Primary key (station_uuid) and (station_uuid, timeseries, ts_utc)."""

    def __init__(self) -> None:
        self.stations: dict[str, StationRow] = {}
        self.measurements: dict[tuple[str, str, datetime], MeasurementRow] = {}
        self.etags: dict[str, tuple[str, datetime]] = {}

    def migrate(self) -> None:
        return None

    def upsert_stations(self, rows: list[StationRow]) -> int:
        for row in rows:
            as_utc(row.fetched_at)
            self.stations[row.station_uuid] = row
        return len(rows)

    def upsert_measurements(self, rows: list[MeasurementRow]) -> int:
        for row in rows:
            ts_utc = as_utc(row.ts_utc)
            as_utc(row.fetched_at)
            stored = MeasurementRow(
                station_uuid=row.station_uuid,
                timeseries=row.timeseries,
                ts_utc=ts_utc,
                value=row.value,
                unit=row.unit,
                state_mnw_mhw=row.state_mnw_mhw,
                state_nsw_hsw=row.state_nsw_hsw,
                source=row.source,
                source_url=row.source_url,
                licence=row.licence,
                fetched_at=as_utc(row.fetched_at),
            )
            key = (stored.station_uuid, stored.timeseries, stored.ts_utc)
            previous = self.measurements.get(key)
            if previous is not None:
                stored = MeasurementRow(
                    station_uuid=stored.station_uuid,
                    timeseries=stored.timeseries,
                    ts_utc=stored.ts_utc,
                    value=stored.value,
                    unit=stored.unit if stored.unit is not None else previous.unit,
                    state_mnw_mhw=(
                        stored.state_mnw_mhw
                        if stored.state_mnw_mhw is not None
                        else previous.state_mnw_mhw
                    ),
                    state_nsw_hsw=(
                        stored.state_nsw_hsw
                        if stored.state_nsw_hsw is not None
                        else previous.state_nsw_hsw
                    ),
                    source=stored.source,
                    source_url=stored.source_url,
                    licence=stored.licence,
                    fetched_at=stored.fetched_at,
                )
            self.measurements[key] = stored
        return len(rows)

    def get_etag(self, cache_key: str) -> str | None:
        found = self.etags.get(cache_key)
        if found is None:
            return None
        return found[0]

    def put_etag(self, cache_key: str, etag: str, fetched_at: datetime) -> None:
        self.etags[cache_key] = (etag, as_utc(fetched_at))
