-- EU live watch, cells re-chosen after review (PR #78): 060's table stays, this one replaces it in 064.
-- Each cell was checked against a known long-term mean flow: GloFAS 2013-2022 daily mean of the
-- cell (Open-Meteo Flood API, queried 2026-10-27) vs the long-term mean at the city. Table per point
-- in ingestion/feeds/README.md. Changed from 060: Rhone/Lyon, Po/Piacenza, Danube/Vienna and
-- Meuse/Liege moved to the main-channel cell; Guadalquivir/Seville dropped (best cell 17 vs ~160 m3/s).
-- Point order (location_id 0..10; Open-Meteo omits location_id for the first point):
--   0 EU01 Seine/Paris, 1 EU02 Rhone/Lyon, 2 EU03 Loire/Orleans, 3 EU04 Po/Piacenza,
--   4 EU05 Ebro/Zaragoza, 5 EU06 Vistula/Warsaw, 6 EU07 Danube/Vienna, 7 EU08 Danube/Budapest,
--   8 EU09 Tisza/Szeged, 9 EU10 Meuse/Liege, 10 EU11 Vltava/Prague.
-- Data: Open-Meteo Flood API (GloFAS), CC BY 4.0, free API non-commercial only. Model output.
CREATE LIGHTNING REST TABLE eu_watch_live_v2 FROM OPENMETEO_FLOOD REQUEST (
  endpoint "https://flood-api.open-meteo.com/v1/flood?latitude=48.925,45.775,47.875,45.075,41.625,52.275,48.175,47.475,46.275,50.675,50.125&longitude=2.275,4.825,1.875,9.625,-0.825,20.975,16.475,19.025,20.125,5.625,14.375&daily=river_discharge&past_days=30&forecast_days=7&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
