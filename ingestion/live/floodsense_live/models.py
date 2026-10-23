"""Rows the poller stores. Timestamps on measurements are UTC."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Station:
    """Station metadata parsed from a PEGELONLINE station object."""

    uuid: str
    number: str
    shortname: str
    longname: str
    water_shortname: str
    water_longname: str
    latitude: float | None
    longitude: float | None
    km: float | None
    agency: str | None
    gauge_zero_value: float | None
    gauge_zero_unit: str | None
    gauge_zero_valid_from: str | None
    equidistance: int | None


@dataclass(frozen=True)
class Measurement:
    """One reading. `ts_utc` is timezone-aware UTC."""

    station_uuid: str
    timeseries: str
    ts_utc: datetime
    value: float | None
    unit: str | None
    state_mnw_mhw: str | None
    state_nsw_hsw: str | None


@dataclass(frozen=True)
class Provenance:
    source: str
    source_url: str
    licence: str
    fetched_at: datetime


@dataclass(frozen=True)
class StationRow:
    station_uuid: str
    number: str
    shortname: str
    longname: str
    water_shortname: str
    water_longname: str
    latitude: float | None
    longitude: float | None
    km: float | None
    agency: str | None
    gauge_zero_value: float | None
    gauge_zero_unit: str | None
    gauge_zero_valid_from: str | None
    equidistance: int | None
    source: str
    source_url: str
    licence: str
    fetched_at: datetime


@dataclass(frozen=True)
class MeasurementRow:
    station_uuid: str
    timeseries: str
    ts_utc: datetime
    value: float | None
    unit: str | None
    state_mnw_mhw: str | None
    state_nsw_hsw: str | None
    source: str
    source_url: str
    licence: str
    fetched_at: datetime


def station_row(station: Station, provenance: Provenance) -> StationRow:
    return StationRow(
        station_uuid=station.uuid,
        number=station.number,
        shortname=station.shortname,
        longname=station.longname,
        water_shortname=station.water_shortname,
        water_longname=station.water_longname,
        latitude=station.latitude,
        longitude=station.longitude,
        km=station.km,
        agency=station.agency,
        gauge_zero_value=station.gauge_zero_value,
        gauge_zero_unit=station.gauge_zero_unit,
        gauge_zero_valid_from=station.gauge_zero_valid_from,
        equidistance=station.equidistance,
        source=provenance.source,
        source_url=provenance.source_url,
        licence=provenance.licence,
        fetched_at=provenance.fetched_at,
    )


def measurement_row(measurement: Measurement, provenance: Provenance) -> MeasurementRow:
    return MeasurementRow(
        station_uuid=measurement.station_uuid,
        timeseries=measurement.timeseries,
        ts_utc=measurement.ts_utc,
        value=measurement.value,
        unit=measurement.unit,
        state_mnw_mhw=measurement.state_mnw_mhw,
        state_nsw_hsw=measurement.state_nsw_hsw,
        source=provenance.source,
        source_url=provenance.source_url,
        licence=provenance.licence,
        fetched_at=provenance.fetched_at,
    )
