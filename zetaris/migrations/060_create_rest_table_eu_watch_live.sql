-- EU live watch: twelve GloFAS river points outside Germany in one Open-Meteo Flood API request.
-- past_days=30 and forecast_days=7, so every query Zetaris runs re-fetches the current series.
-- Table only. The view is floodsense.eu_watch (061), its seed twin floodsense_seed.eu_watch (062).
-- Point order (location_id 0..11; Open-Meteo omits location_id for the first point):
--   0 EU01 Seine/Paris, 1 EU02 Rhone/Lyon, 2 EU03 Loire/Orleans, 3 EU04 Po/Piacenza,
--   4 EU05 Ebro/Zaragoza, 5 EU06 Vistula/Warsaw, 6 EU07 Danube/Vienna, 7 EU08 Danube/Budapest,
--   8 EU09 Tisza/Szeged, 9 EU10 Meuse/Liege, 10 EU11 Vltava/Prague, 11 EU12 Guadalquivir/Seville.
-- Coordinates are GloFAS 0.05 deg cell centres on the river within about 6 km of each city:
-- the cell with the largest past-30-day median discharge among the 3x3 cells around the city
-- (checked against the API on 2026-10-27; the city-centre cell is often a small side cell).
-- Numbers start at 060, not 053, to leave room for parallel branches.
-- Data: Open-Meteo Flood API (GloFAS), CC BY 4.0, free API non-commercial only. Model output,
-- not a gauge reading and not an official warning.
CREATE LIGHTNING REST TABLE eu_watch_live FROM OPENMETEO_FLOOD REQUEST (
  endpoint "https://flood-api.open-meteo.com/v1/flood?latitude=48.925,45.725,47.875,45.125,41.625,52.275,48.175,47.475,46.275,50.675,50.125,37.325&longitude=2.275,4.775,1.875,9.725,-0.825,20.975,16.425,19.025,20.125,5.575,14.375,-6.075&daily=river_discharge&past_days=30&forecast_days=7&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
