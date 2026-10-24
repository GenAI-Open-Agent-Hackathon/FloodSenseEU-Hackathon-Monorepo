-- view: floodsense.hazard_timeline
-- columns: point_id string, ts_utc timestamp, rain_mm double, discharge_m3s double, warning_level string
-- min_rows: 3264
-- One row per point per hour: hourly rain (006) joined to that day's discharge (004), so the daily
-- discharge value repeats for the 24 hours of its day. 8 points x 408 hours = 3264 rows.
-- warning_level stays NULL until an AEMET source exists; it is the only column AEMET would fill.
-- ts_utc: Open-Meteo returns hours without a zone, and the request in 006 asks for GMT. Zetaris casts
-- them in its session time zone, which is GMT in the local stack (SELECT current_timezone()).
-- location_id is the request order in 006; it arrives as NULL for the first point.
CREATE OR REPLACE SCHEMASTORE VIEW hazard_timeline WITH CONTAINER floodsense AS
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
  FROM OPENMETEO_ARCHIVE.rain_archive g
  LATERAL VIEW posexplode(g.hourly.time) t AS pos, stamp
) r
LEFT JOIN floodsense.discharge_daily d
  ON d.point_id = r.point_id AND d.date = CAST(r.ts_utc AS DATE)
