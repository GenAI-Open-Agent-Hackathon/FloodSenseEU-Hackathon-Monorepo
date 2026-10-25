-- view: floodsense.hazard_now
-- columns: point_id string, ts_utc timestamp, rain_mm double, discharge_m3s double, warning_level string
-- min_rows: 1152
-- The rolling-window twin of 007. Same columns, so a caller changes the view name and nothing else.
-- 007 reads the REST tables of 003 and 006, whose endpoints pin start_date/end_date to the 2024 event.
-- This one reads the live tables of 030 and 032 instead, which carry past_days/forecast_days, so every
-- query re-fetches Open-Meteo and the rows move with the clock. Nothing is stored or cached here.
-- The window is the rain table's: past_days=3 + forecast_days=3 = 144 hours x 8 points = 1152 rows.
-- 030 covers 14 days, which contains that window, so every hour finds its day's discharge.
-- Discharge is joined inline rather than through a view of its own: a floodsense.* view owes a seed twin
-- and a contracts/views.yaml entry, and one daily view would buy nothing that this subquery does not.
-- river_discharge is the control run, as in 004. 030 also returns river_discharge_max; a column for it
-- would change the shape this view shares with 007, so it stays out until 007 carries one too.
-- warning_level is NULL for the same reason as in 007: no AEMET source fills it yet.
-- Point order is the request order of 030 and 032 (0 VAL01 ... 7 VAL08), and Open-Meteo omits
-- location_id for the first point, so COALESCE maps that NULL to 0.
-- Data: Open-Meteo forecast and flood APIs, CC BY 4.0, free API non-commercial only.
CREATE OR REPLACE SCHEMASTORE VIEW hazard_now WITH CONTAINER floodsense AS
SELECT
  r.point_id,
  r.ts_utc,
  r.rain_mm,
  d.discharge_m3s,
  CAST(NULL AS STRING) AS warning_level
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
