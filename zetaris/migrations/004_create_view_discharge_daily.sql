-- view: floodsense.discharge_daily
-- columns: point_id string, date date, discharge_m3s double, source string
-- min_rows: 136
-- One row per point per day. Values come back from REST as strings, so every column is cast.
-- location_id is the request order in 003. Open-Meteo leaves it out for the first point, so it
-- arrives as NULL there: COALESCE maps it to 0.
CREATE OR REPLACE SCHEMASTORE VIEW discharge_daily WITH CONTAINER floodsense AS
SELECT
  CASE COALESCE(g.location_id, 0)
    WHEN 0 THEN 'VAL01' WHEN 1 THEN 'VAL02' WHEN 2 THEN 'VAL03' WHEN 3 THEN 'VAL04'
    WHEN 4 THEN 'VAL05' WHEN 5 THEN 'VAL06' WHEN 6 THEN 'VAL07' WHEN 7 THEN 'VAL08'
  END AS point_id,
  CAST(t.day AS DATE) AS date,
  CAST(g.daily.river_discharge[t.pos] AS DOUBLE) AS discharge_m3s,
  'open-meteo-flood-glofas' AS source
FROM OPENMETEO_FLOOD.glofas_discharge g
LATERAL VIEW posexplode(g.daily.time) t AS pos, day
