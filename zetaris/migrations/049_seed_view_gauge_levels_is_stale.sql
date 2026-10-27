-- view: floodsense_seed.gauge_levels
-- columns: station string, water string, ts_utc timestamp, level_cm double, source string, river_km double, lat double, lon double, trend_cm_h double, mnw_cm double, mw_cm double, mhw_cm double, hhw_cm double, hsw_cm double, band string, fetched_at timestamp, is_stale boolean
-- min_rows: 3
-- 049 = 047 plus is_stale. Seed rows are never current, so it is always true.
-- Same rows as 043, with the 046 columns. No reading is invented: level, trend and band stay
-- NULL / unknown. Position and characteristic values are the station metadata PEGELONLINE
-- published on 2026-10-27 (they describe the gauge, not the 2021 event).
-- Licence DL-DE->Zero-2.0. Quelle: WSV, PEGELONLINE. docs/legal/sources.md.
CREATE OR REPLACE SCHEMASTORE VIEW gauge_levels WITH CONTAINER floodsense_seed AS
SELECT
  station,
  water,
  CAST(ts_utc AS TIMESTAMP) AS ts_utc,
  CAST(NULL AS DOUBLE) AS level_cm,
  source,
  CAST(river_km AS DOUBLE) AS river_km,
  CAST(lat AS DOUBLE) AS lat,
  CAST(lon AS DOUBLE) AS lon,
  CAST(NULL AS DOUBLE) AS trend_cm_h,
  CAST(mnw_cm AS DOUBLE) AS mnw_cm,
  CAST(mw_cm AS DOUBLE) AS mw_cm,
  CAST(mhw_cm AS DOUBLE) AS mhw_cm,
  CAST(hhw_cm AS DOUBLE) AS hhw_cm,
  CAST(hsw_cm AS DOUBLE) AS hsw_cm,
  'unknown' AS band,
  CAST(NULL AS TIMESTAMP) AS fetched_at,
  true AS is_stale
FROM VALUES
  ('BONN', 'RHEIN', '2021-07-12 00:00:00', 'seed:pegelonline', 654.8, 50.736398, 7.108045, 121.0, 290.0, 680.0, 1013.0, CAST(NULL AS DOUBLE)),
  ('KÃ–LN', 'RHEIN', '2021-07-12 00:00:00', 'seed:pegelonline', 688.0, 50.936949, 6.9633, 114.0, 297.0, 725.0, 1069.0, 830.0),
  ('KOBLENZ', 'RHEIN', '2021-07-12 00:00:00', 'seed:pegelonline', 591.49, 50.35864, 7.604741, 60.0, 214.0, 588.0, 949.0, 650.0)
AS t(station, water, ts_utc, source, river_km, lat, lon, mnw_cm, mw_cm, mhw_cm, hhw_cm, hsw_cm)
