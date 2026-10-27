-- view: floodsense_seed.eu_watch
-- columns: point_id string, name string, country string, river string, lat double, lon double, discharge_m3s double, forecast_max_m3s double, past30_median_m3s double, band string, basis string, source string, as_of_date date
-- min_rows: 12
-- Seed twin of 061: the twelve points and their positions only. No discharge is invented:
-- the values stay NULL and band is unknown, so a seed run says it has no current reading.
-- Data: Open-Meteo Flood API (GloFAS), CC BY 4.0. Positions as in 060.
CREATE OR REPLACE SCHEMASTORE VIEW eu_watch WITH CONTAINER floodsense_seed AS
SELECT
  point_id,
  name,
  country,
  river,
  CAST(lat AS DOUBLE) AS lat,
  CAST(lon AS DOUBLE) AS lon,
  CAST(NULL AS DOUBLE) AS discharge_m3s,
  CAST(NULL AS DOUBLE) AS forecast_max_m3s,
  CAST(NULL AS DOUBLE) AS past30_median_m3s,
  'unknown' AS band,
  'model, not an official warning: seed row, no reading' AS basis,
  'seed:openmeteo_flood' AS source,
  CAST(NULL AS DATE) AS as_of_date
FROM VALUES
  ('EU01', 'Paris', 'FR', 'Seine', 48.925, 2.275),
  ('EU02', 'Lyon', 'FR', 'Rhone', 45.725, 4.775),
  ('EU03', 'Orleans', 'FR', 'Loire', 47.875, 1.875),
  ('EU04', 'Piacenza', 'IT', 'Po', 45.125, 9.725),
  ('EU05', 'Zaragoza', 'ES', 'Ebro', 41.625, -0.825),
  ('EU06', 'Warsaw', 'PL', 'Vistula', 52.275, 20.975),
  ('EU07', 'Vienna', 'AT', 'Danube', 48.175, 16.425),
  ('EU08', 'Budapest', 'HU', 'Danube', 47.475, 19.025),
  ('EU09', 'Szeged', 'HU', 'Tisza', 46.275, 20.125),
  ('EU10', 'Liege', 'BE', 'Meuse', 50.675, 5.575),
  ('EU11', 'Prague', 'CZ', 'Vltava', 50.125, 14.375),
  ('EU12', 'Seville', 'ES', 'Guadalquivir', 37.325, -6.075)
AS t(point_id, name, country, river, lat, lon)
