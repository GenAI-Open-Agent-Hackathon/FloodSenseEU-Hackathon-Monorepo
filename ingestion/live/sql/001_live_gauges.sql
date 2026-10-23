-- Idempotent DDL for PEGELONLINE gauges.
-- The poller applies this file on every run. Compose also mounts it into
-- docker-entrypoint-initdb.d, which runs only when the data volume is empty.
-- Safe to re-run. No passwords in this file.

CREATE SCHEMA IF NOT EXISTS live;

CREATE TABLE IF NOT EXISTS live.gauge_station (
    station_uuid text PRIMARY KEY,
    number text NOT NULL,
    shortname text NOT NULL,
    longname text NOT NULL,
    water_shortname text NOT NULL,
    water_longname text NOT NULL,
    latitude double precision,
    longitude double precision,
    km double precision,
    agency text,
    gauge_zero_value double precision,
    gauge_zero_unit text,
    gauge_zero_valid_from text,
    equidistance integer,
    source text NOT NULL,
    source_url text NOT NULL,
    licence text NOT NULL,
    fetched_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS live.gauge_measurement (
    station_uuid text NOT NULL REFERENCES live.gauge_station (station_uuid),
    timeseries text NOT NULL,
    ts_utc timestamptz NOT NULL,
    value double precision,
    unit text,
    state_mnw_mhw text,
    state_nsw_hsw text,
    source text NOT NULL,
    source_url text NOT NULL,
    licence text NOT NULL,
    fetched_at timestamptz NOT NULL,
    PRIMARY KEY (station_uuid, timeseries, ts_utc)
);

CREATE INDEX IF NOT EXISTS gauge_measurement_ts_utc_idx
    ON live.gauge_measurement (ts_utc);

-- ETags for If-None-Match. Not a Zetaris table. Internal to the poller.
CREATE TABLE IF NOT EXISTS live.gauge_http_cache (
    cache_key text PRIMARY KEY,
    etag text NOT NULL,
    fetched_at timestamptz NOT NULL
);

COMMENT ON TABLE live.gauge_station IS
    'PEGELONLINE station metadata. Raw source, licence DL-DE->Zero-2.0.';

COMMENT ON TABLE live.gauge_measurement IS
    'PEGELONLINE readings. W is water level in cm, raw and unchecked.';

COMMENT ON COLUMN live.gauge_measurement.ts_utc IS
    'Measurement timestamp normalised to UTC.';

COMMENT ON COLUMN live.gauge_measurement.licence IS
    'Short licence name. PEGELONLINE uses DL-DE->Zero-2.0.';
