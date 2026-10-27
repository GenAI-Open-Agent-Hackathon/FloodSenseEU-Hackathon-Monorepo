-- view: floodsense.gauge_levels
-- columns: station string, water string, ts_utc timestamp, level_cm double, source string, river_km double, lat double, lon double, trend_cm_h double, mnw_cm double, mw_cm double, mhw_cm double, hhw_cm double, hsw_cm double, band string, fetched_at timestamp
-- min_rows: 0
-- Current PEGELONLINE water level per station, read from 045 (pegel_poll.py writes the CSV).
-- The first five columns are the 037 columns, unchanged. Added: river km, position, trend in cm
-- per hour over about the last hour, the station's characteristic values in cm (MNW, MW, MHW, HHW,
-- HSW; NULL where PEGELONLINE has none), band (below / near / above against MHW, or unknown),
-- and fetched_at. Stations: Rhine Mainz..Duesseldorf, Mosel Trier UP and Cochem.
-- The Ahr is not on PEGELONLINE (state gauges, Rhineland-Palatinate), so it stays replay only.
-- min_rows is 0 so verify passes on a laptop where the poller has not run.
-- Licence DL-DE->Zero-2.0. Quelle: WSV, PEGELONLINE. docs/legal/sources.md.
CREATE OR REPLACE SCHEMASTORE VIEW gauge_levels WITH CONTAINER floodsense AS
SELECT
  CAST(station AS STRING) AS station,
  CAST(water AS STRING) AS water,
  CAST(ts_utc AS TIMESTAMP) AS ts_utc,
  CAST(level_cm AS DOUBLE) AS level_cm,
  CAST(source AS STRING) AS source,
  CAST(river_km AS DOUBLE) AS river_km,
  CAST(lat AS DOUBLE) AS lat,
  CAST(lon AS DOUBLE) AS lon,
  CAST(trend_cm_h AS DOUBLE) AS trend_cm_h,
  CAST(mnw_cm AS DOUBLE) AS mnw_cm,
  CAST(mw_cm AS DOUBLE) AS mw_cm,
  CAST(mhw_cm AS DOUBLE) AS mhw_cm,
  CAST(hhw_cm AS DOUBLE) AS hhw_cm,
  CAST(hsw_cm AS DOUBLE) AS hsw_cm,
  CAST(band AS STRING) AS band,
  CAST(fetched_at AS TIMESTAMP) AS fetched_at
FROM floodsense_live_src.pegel_now_src
