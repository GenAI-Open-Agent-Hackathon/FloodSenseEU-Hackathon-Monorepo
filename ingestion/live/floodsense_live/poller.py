"""One poll cycle: fetch, normalise to UTC, upsert."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

from floodsense_live.config import Config
from floodsense_live.http import FetchResult, HttpError, PegelClient
from floodsense_live.models import Measurement, Provenance, Station, measurement_row, station_row
from floodsense_live.parse import (
    LICENCE,
    SOURCE,
    ParseError,
    parse_measurements,
    parse_station,
    parse_station_list,
)
from floodsense_live.store import GaugeStore

Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]


class PollError(RuntimeError):
    """A station failed after retries. Nothing partial is hidden: the run stops."""


@dataclass(frozen=True)
class Sample:
    shortname: str
    timeseries: str
    ts_utc: datetime
    value: float | None


@dataclass
class PollResult:
    stations_upserted: int = 0
    measurements_upserted: int = 0
    not_modified: int = 0
    requests: int = 0
    samples: list[Sample] | None = None

    def __post_init__(self) -> None:
        if self.samples is None:
            self.samples = []


def station_document_url(base_url: str, shortname: str) -> str:
    quoted = quote(shortname, safe="")
    return (
        f"{base_url}/stations/{quoted}.json"
        "?includeTimeseries=true&includeCurrentMeasurement=true"
    )


def measurements_url(base_url: str, station_uuid: str, timeseries: str, lookback: str) -> str:
    return (
        f"{base_url}/stations/{quote(station_uuid, safe='')}"
        f"/{quote(timeseries, safe='')}/measurements.json?start={quote(lookback, safe='')}"
    )


def all_current_url(base_url: str, timeseries: str) -> str:
    return (
        f"{base_url}/stations.json?timeseries={quote(timeseries, safe='')}"
        "&includeTimeseries=true&includeCurrentMeasurement=true"
    )


def poll_once(
    config: Config,
    client: PegelClient,
    store: GaugeStore,
    *,
    now: Clock | None = None,
    pause: Sleeper | None = None,
) -> PollResult:
    clock = (lambda: datetime.now(timezone.utc)) if now is None else now
    waiter = (lambda _seconds: None) if pause is None else pause
    store.migrate()
    result = PollResult()
    calls = {"n": 0}

    def wait() -> None:
        if calls["n"] and config.pause_seconds:
            waiter(config.pause_seconds)
        calls["n"] += 1

    if config.all_current:
        _poll_all_current(config, client, store, result, clock, wait)
        return result
    for shortname in config.stations:
        _poll_station(config, client, store, result, clock, wait, shortname)
    return result


def _poll_all_current(
    config: Config,
    client: PegelClient,
    store: GaugeStore,
    result: PollResult,
    clock: Clock,
    wait: Callable[[], None],
) -> None:
    # One list call per configured series. Default is W only.
    for name in config.timeseries:
        url = all_current_url(config.base_url, name)
        fetched = _fetch(client, store, result, clock, wait, url)
        if fetched.not_modified:
            continue
        try:
            parsed = parse_station_list(fetched.payload, timeseries=(name,))
        except ParseError as exc:
            raise PollError(f"could not parse station list: {exc}") from exc
        _store_parsed(store, result, clock, url, parsed)
        _ack(store, fetched, clock)


def _poll_station(
    config: Config,
    client: PegelClient,
    store: GaugeStore,
    result: PollResult,
    clock: Clock,
    wait: Callable[[], None],
    shortname: str,
) -> None:
    station_url = station_document_url(config.base_url, shortname)
    fetched = _fetch(client, store, result, clock, wait, station_url)
    station: Station | None = None
    currents: list[Measurement] = []
    if not fetched.not_modified:
        try:
            station, currents = parse_station(fetched.payload, timeseries=config.timeseries)
        except ParseError as exc:
            raise PollError(f"{shortname}: {exc}") from exc
        _store_parsed(store, result, clock, station_url, [(station, [])])
        _ack(store, fetched, clock)
    if station is None:
        # 304. History is still requested. The station row is already stored.
        station_uuid = _uuid_from_store(store, shortname)
        if station_uuid is None:
            raise PollError(
                f"{shortname}: HTTP 304 but no station row is stored yet. "
                "Clear live.gauge_http_cache or run again after a 200."
            )
    else:
        station_uuid = station.uuid
    for name in config.timeseries:
        url = measurements_url(config.base_url, station_uuid, name, config.lookback)
        body = _fetch(client, store, result, clock, wait, url)
        if body.not_modified:
            continue
        unit = _unit_from_currents(currents, name)
        try:
            history = parse_measurements(
                body.payload,
                station_uuid=station_uuid,
                timeseries=name,
                unit=unit,
            )
        except ParseError as exc:
            raise PollError(f"{shortname} {name}: {exc}") from exc
        label = shortname if station is None else station.shortname
        _store_measurements(store, result, clock, url, label, history)
        _ack(store, body, clock)
    if currents and station is not None:
        # Current readings carry state flags the history array does not.
        # Written last so those flags win on the shared timestamp.
        _store_measurements(store, result, clock, station_url, station.shortname, currents)


def _uuid_from_store(store: GaugeStore, shortname: str) -> str | None:
    stations = getattr(store, "stations", None)
    if isinstance(stations, dict):
        for row in stations.values():
            if row.shortname.upper() == shortname.upper():
                return str(row.station_uuid)
        return None
    # Postgres path: the 304 branch needs the uuid already stored. Query it.
    getter = getattr(store, "station_uuid_for_shortname", None)
    if getter is None:
        return None
    found = getter(shortname)
    if found is None:
        return None
    return str(found)


def _unit_from_currents(currents: list[Measurement], timeseries: str) -> str | None:
    for measurement in currents:
        if measurement.timeseries.upper() == timeseries.upper():
            return measurement.unit
    return None


def _store_parsed(
    store: GaugeStore,
    result: PollResult,
    clock: Clock,
    url: str,
    parsed: list[tuple[Station, list[Measurement]]],
) -> None:
    fetched_at = clock()
    provenance = Provenance(
        source=SOURCE,
        source_url=url,
        licence=LICENCE,
        fetched_at=fetched_at,
    )
    stations = [station_row(station, provenance) for station, _currents in parsed]
    result.stations_upserted += store.upsert_stations(stations)
    measurements: list[Measurement] = []
    for station, currents in parsed:
        measurements.extend(currents)
        _remember_sample(result, station.shortname, currents)
    if measurements:
        rows = [measurement_row(item, provenance) for item in measurements]
        result.measurements_upserted += store.upsert_measurements(rows)


def _store_measurements(
    store: GaugeStore,
    result: PollResult,
    clock: Clock,
    url: str,
    shortname: str,
    measurements: list[Measurement],
) -> None:
    if not measurements:
        return
    provenance = Provenance(
        source=SOURCE,
        source_url=url,
        licence=LICENCE,
        fetched_at=clock(),
    )
    rows = [measurement_row(item, provenance) for item in measurements]
    result.measurements_upserted += store.upsert_measurements(rows)
    _remember_sample(result, shortname, measurements)


def _remember_sample(result: PollResult, shortname: str, measurements: list[Measurement]) -> None:
    assert result.samples is not None
    for measurement in measurements:
        if len(result.samples) >= 5:
            return
        result.samples.append(
            Sample(
                shortname=shortname,
                timeseries=measurement.timeseries,
                ts_utc=measurement.ts_utc,
                value=measurement.value,
            )
        )


def _fetch(
    client: PegelClient,
    store: GaugeStore,
    result: PollResult,
    clock: Clock,
    wait: Callable[[], None],
    url: str,
) -> FetchResult:
    wait()
    result.requests += 1
    try:
        fetched = client.fetch_json(url, etag=store.get_etag(url))
    except HttpError as exc:
        raise PollError(str(exc)) from exc
    if fetched.not_modified:
        result.not_modified += 1
        # A 304 has no body to store. Remember the validator immediately.
        _ack(store, fetched, clock)
    return fetched


def _ack(store: GaugeStore, fetched: FetchResult, clock: Clock) -> None:
    """Remember the ETag only after a successful read or a 304.

    Saving it before the upsert would make the next poll skip a body that
    never landed in the database.
    """
    if fetched.etag:
        store.put_etag(fetched.url, fetched.etag, clock())
