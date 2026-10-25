-- view: floodsense.hazard_now
-- columns: point_id string, ts_utc timestamp, rain_mm double, discharge_m3s double, warning_level string, horizon string
-- min_rows: 1152
-- Replaces the select list of 034. Same 1152 rows (8 points x 144 hours). Adds horizon so a
-- rolling-window hour is labelled, not left looking like the pinned 2024 archive in 007.
-- 032 asks the forecast API for past_days=3 and forecast_days=3. The payload has no flag on
-- the hour. An hour at or before the engine clock is observed. An hour after it is forecast.
-- The local stack session zone is GMT (007, current_timezone()), and 032 requests timezone=GMT,
-- so current_timestamp() and ts_utc are the same clock.
-- horizon follows the rain hour. The day's river_discharge is still joined for every hour of
-- that date, including a forecast hour. It is not a second label.
-- The seed twin is 040. It does not use this clock. Inventing a present there is refused.
-- Data: Open-Meteo forecast and flood APIs, CC BY 4.0, free API non-commercial only.
-- Attribution: Weather data by Open-Meteo.com. Provenance row ds_open_meteo_forecast.
CREATE OR REPLACE SCHEMASTORE VIEW hazard_now WITH CONTAINER floodsense AS
SELECT
  r.point_id,
  r.ts_utc,
  r.rain_mm,
  d.discharge_m3s,
  CAST(NULL AS STRING) AS warning_level,
  CASE
    WHEN r.ts_utc > current_timestamp() THEN 'forecast'
    ELSE 'observed'
  END AS horizon
FROM (
  SELECT
    CASE COALESCE(g.location_id, 0)
      WHEN 0 THEN 'VAL01' WHEN 1 THEN 'VAL02' WHEN 2 THEN 'VAL03' WHEN 3 THEN 'VAL04'
      WHEN 4 THEN 'VAL05' WHEN 5 THEN 'VAL06' WHEN 6 THEN 'VAL07' WHEN 7 THEN 'VAL08'
    END AS point_id,
    CAST(t.stamp AS TIMESTAMP) AS ts_utc,
    CAST(g.hourly.precipitation[t.pos] AS DOUBLE) AS rain_mm
  FROM OPENMETEO_FORECAST.rain_live g
  LATERAL VIEW posexplode(g.hourly.time) t AS pos, stamp
) r
LEFT JOIN (
  SELECT
    CASE COALESCE(f.location_id, 0)
      WHEN 0 THEN 'VAL01' WHEN 1 THEN 'VAL02' WHEN 2 THEN 'VAL03' WHEN 3 THEN 'VAL04'
      WHEN 4 THEN 'VAL05' WHEN 5 THEN 'VAL06' WHEN 6 THEN 'VAL07' WHEN 7 THEN 'VAL08'
    END AS point_id,
    CAST(u.day AS DATE) AS date,
    CAST(f.daily.river_discharge[u.pos] AS DOUBLE) AS discharge_m3s
  FROM OPENMETEO_FLOOD.glofas_discharge_live f
  LATERAL VIEW posexplode(f.daily.time) u AS pos, day
) d
  ON d.point_id = r.point_id AND d.date = CAST(r.ts_utc AS DATE)
