"""Parse PEGELONLINE JSON into stations and measurements."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from floodsense_live.models import Measurement, Station

SOURCE = "PEGELONLINE"
LICENCE = "DL-DE->Zero-2.0"
LICENCE_URL = "https://www.govdata.de/dl-de/zero-2-0"
DEFAULT_BASE_URL = "https://pegelonline.wsv.de/webservices/rest-api/v2"


class ParseError(ValueError):
    """The payload was JSON but not the shape this poller stores."""


def parse_timestamp(value: object) -> datetime:
    """Return a timezone-aware UTC datetime.

    PEGELONLINE sends an offset (for example +02:00 in summer). A trailing
    Z is accepted so the same function works on Python 3.10, whose
    fromisoformat does not accept Z. A timestamp with no offset is rejected
    rather than guessed as local time.
    """
    if not isinstance(value, str) or not value.strip():
        raise ParseError(f"timestamp must be a string, got {value!r}")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ParseError(f"timestamp is not ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        raise ParseError(f"timestamp has no offset: {value}")
    return parsed.astimezone(timezone.utc)


def _number(value: object, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ParseError(f"{field} must be a number, got {value!r}")
    return float(value)


def _text(value: object, *, field: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ParseError(f"missing {field}")
        return None
    if not isinstance(value, str):
        value = str(value)
    if required and not value:
        raise ParseError(f"missing {field}")
    return value


def _required(value: object, *, field: str) -> str:
    text = _text(value, field=field, required=True)
    if not text:
        raise ParseError(f"missing {field}")
    return text


def _object(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ParseError(f"{field} must be an object")
    return value


def _series_by_name(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("timeseries") or []
    if not isinstance(raw, list):
        raise ParseError("timeseries must be an array")
    series: list[dict[str, Any]] = []
    for item in raw:
        series.append(_object(item, field="timeseries item"))
    return series


def parse_station(
    payload: object,
    *,
    timeseries: tuple[str, ...],
) -> tuple[Station, list[Measurement]]:
    """Parse one station object. Current readings are kept for `timeseries` only."""
    body = _object(payload, field="station")
    uuid = _required(body.get("uuid"), field="uuid")
    number = _required(body.get("number"), field="number")
    shortname = _required(body.get("shortname"), field="shortname")
    longname = _text(body.get("longname"), field="longname") or shortname
    water = body.get("water") or {}
    if not isinstance(water, dict):
        raise ParseError("water must be an object")
    wanted = {name.upper() for name in timeseries}
    chosen: dict[str, Any] | None = None
    currents: list[Measurement] = []
    for series in _series_by_name(body):
        name = _required(series.get("shortname"), field="timeseries.shortname")
        if name.upper() not in wanted:
            continue
        if chosen is None:
            chosen = series
        current = series.get("currentMeasurement")
        if current is None:
            continue
        current_body = _object(current, field="currentMeasurement")
        currents.append(
            Measurement(
                station_uuid=uuid,
                timeseries=name,
                ts_utc=parse_timestamp(current_body.get("timestamp")),
                value=_number(current_body.get("value"), field="value"),
                unit=_text(series.get("unit"), field="unit"),
                state_mnw_mhw=_text(current_body.get("stateMnwMhw"), field="stateMnwMhw"),
                state_nsw_hsw=_text(current_body.get("stateNswHsw"), field="stateNswHsw"),
            )
        )
    gauge_zero_value = None
    gauge_zero_unit = None
    gauge_zero_valid_from = None
    equidistance = None
    if chosen is not None:
        equidistance_raw = chosen.get("equidistance")
        if equidistance_raw is not None:
            if isinstance(equidistance_raw, bool) or not isinstance(equidistance_raw, int):
                raise ParseError(f"equidistance must be an integer, got {equidistance_raw!r}")
            equidistance = equidistance_raw
        gauge = chosen.get("gaugeZero")
        if gauge is not None:
            gauge_body = _object(gauge, field="gaugeZero")
            gauge_zero_value = _number(gauge_body.get("value"), field="gaugeZero.value")
            gauge_zero_unit = _text(gauge_body.get("unit"), field="gaugeZero.unit")
            gauge_zero_valid_from = _text(
                gauge_body.get("validFrom"),
                field="gaugeZero.validFrom",
            )
    station = Station(
        uuid=uuid,
        number=number,
        shortname=shortname,
        longname=longname,
        water_shortname=_text(water.get("shortname"), field="water.shortname") or "",
        water_longname=_text(water.get("longname"), field="water.longname") or "",
        latitude=_number(body.get("latitude"), field="latitude"),
        longitude=_number(body.get("longitude"), field="longitude"),
        km=_number(body.get("km"), field="km"),
        agency=_text(body.get("agency"), field="agency"),
        gauge_zero_value=gauge_zero_value,
        gauge_zero_unit=gauge_zero_unit,
        gauge_zero_valid_from=gauge_zero_valid_from,
        equidistance=equidistance,
    )
    return station, currents


def parse_station_list(
    payload: object,
    *,
    timeseries: tuple[str, ...],
) -> list[tuple[Station, list[Measurement]]]:
    if not isinstance(payload, list):
        raise ParseError("station list must be a JSON array")
    return [parse_station(item, timeseries=timeseries) for item in payload]


def parse_measurements(
    payload: object,
    *,
    station_uuid: str,
    timeseries: str,
    unit: str | None,
) -> list[Measurement]:
    """Parse `/measurements.json`, a JSON array of timestamp/value objects."""
    if not isinstance(payload, list):
        raise ParseError("measurements must be a JSON array")
    rows: list[Measurement] = []
    for item in payload:
        body = _object(item, field="measurement")
        rows.append(
            Measurement(
                station_uuid=station_uuid,
                timeseries=timeseries,
                ts_utc=parse_timestamp(body.get("timestamp")),
                value=_number(body.get("value"), field="value"),
                unit=unit,
                state_mnw_mhw=None,
                state_nsw_hsw=None,
            )
        )
    return rows
