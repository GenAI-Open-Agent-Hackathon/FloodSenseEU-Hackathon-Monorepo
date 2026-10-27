-- view: floodsense.eu_watch
-- columns: point_id string, name string, country string, river string, lat double, lon double, discharge_m3s double, forecast_max_m3s double, past30_median_m3s double, band string, basis string, source string, as_of_date date
-- min_rows: 11
-- 064 replaces 061: reads 063's re-chosen cells (11 points, Seville dropped) and computes the
-- past-30-day median exactly (Spark percentile), not with percentile_approx.
-- One row per EU watch point (063), recomputed from the rolling GloFAS series on every query.
-- discharge_m3s: the control-run value for today (GMT). forecast_max_m3s: the highest value from
-- today through the 7-day forecast. past30_median_m3s: the exact median of the 30 past days.
-- All discharge values are GloFAS model cell values, not gauge measurements.
-- band is relative to the series itself, never to an official threshold:
--   above  forecast max >= 2 x past-30-day median
--   near   forecast max >= 1.5 x past-30-day median
--   below  otherwise; unknown when a value is missing or the median is 0.
-- basis carries that label on every row: model, not an official warning.
-- Names are ASCII on purpose (049 showed non-ASCII literals can arrive double-encoded).
-- Data: Open-Meteo Flood API (GloFAS), CC BY 4.0, free API non-commercial only.
CREATE OR REPLACE SCHEMASTORE VIEW eu_watch WITH CONTAINER floodsense AS
SELECT
  p.point_id,
  p.name,
  p.country,
  p.river,
  CAST(p.lat AS DOUBLE) AS lat,
  CAST(p.lon AS DOUBLE) AS lon,
  a.discharge_m3s,
  a.forecast_max_m3s,
  a.past30_median_m3s,
  CASE
    WHEN a.forecast_max_m3s IS NULL OR a.past30_median_m3s IS NULL OR a.past30_median_m3s <= 0 THEN 'unknown'
    WHEN a.forecast_max_m3s >= 2 * a.past30_median_m3s THEN 'above'
    WHEN a.forecast_max_m3s >= 1.5 * a.past30_median_m3s THEN 'near'
    ELSE 'below'
  END AS band,
  'model, not an official warning: GloFAS 7-day forecast max vs 2x past-30-day median' AS basis,
  'Open-Meteo Flood API (GloFAS)' AS source,
  current_date() AS as_of_date
FROM VALUES
  (0, 'EU01', 'Paris', 'FR', 'Seine', 48.925, 2.275),
  (1, 'EU02', 'Lyon', 'FR', 'Rhone', 45.775, 4.825),
  (2, 'EU03', 'Orleans', 'FR', 'Loire', 47.875, 1.875),
  (3, 'EU04', 'Piacenza', 'IT', 'Po', 45.075, 9.625),
  (4, 'EU05', 'Zaragoza', 'ES', 'Ebro', 41.625, -0.825),
  (5, 'EU06', 'Warsaw', 'PL', 'Vistula', 52.275, 20.975),
  (6, 'EU07', 'Vienna', 'AT', 'Danube', 48.175, 16.475),
  (7, 'EU08', 'Budapest', 'HU', 'Danube', 47.475, 19.025),
  (8, 'EU09', 'Szeged', 'HU', 'Tisza', 46.275, 20.125),
  (9, 'EU10', 'Liege', 'BE', 'Meuse', 50.675, 5.625),
  (10, 'EU11', 'Prague', 'CZ', 'Vltava', 50.125, 14.375)
AS p(loc, point_id, name, country, river, lat, lon)
LEFT JOIN (
  SELECT
    s.loc,
    MAX(CASE WHEN s.day = current_date() THEN s.q END) AS discharge_m3s,
    MAX(CASE WHEN s.day >= current_date() THEN s.q END) AS forecast_max_m3s,
    CAST(percentile(CASE WHEN s.day < current_date() THEN s.q END, 0.5) AS DOUBLE) AS past30_median_m3s
  FROM (
    SELECT
      COALESCE(f.location_id, 0) AS loc,
      CAST(u.day AS DATE) AS day,
      CAST(f.daily.river_discharge[u.pos] AS DOUBLE) AS q
    FROM OPENMETEO_FLOOD.eu_watch_live_v2 f
    LATERAL VIEW posexplode(f.daily.time) u AS pos, day
  ) s
  GROUP BY s.loc
) a
  ON a.loc = p.loc
