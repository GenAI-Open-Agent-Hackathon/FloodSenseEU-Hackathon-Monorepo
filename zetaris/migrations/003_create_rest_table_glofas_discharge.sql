-- One REST table over the Open-Meteo Flood API (GloFAS), all eight Valencia points in one request.
-- Points are the rows of ingestion/prep/valencia_points.csv, in this order:
--   0 VAL01  1 VAL02  2 VAL03  3 VAL04  4 VAL05  5 VAL06  6 VAL07  7 VAL08
-- Zetaris flattens the response into one row per point and adds location_id (0..7, request order).
-- The view in 004 maps location_id back to point_id, so keep the order here and there identical.
-- Window: 2024-10-20 to 2024-11-05, days in GMT, around the 29 Oct 2024 event (EMSR773).
-- Open-Meteo snaps each point to its 0.05 degree grid cell, so neighbouring points can share values.
-- Data: Open-Meteo Flood API, CC BY 4.0. Attribution is in the provenance view.
-- Changing a REST table needs a new migration (no OR REPLACE for REST tables).
CREATE LIGHTNING REST TABLE glofas_discharge FROM OPENMETEO_FLOOD REQUEST (
  endpoint "https://flood-api.open-meteo.com/v1/flood?latitude=39.4278,39.4019,39.4267,39.4181,39.4244,39.1906,39.4694,39.5683&longitude=-0.4172,-0.4036,-0.3836,-0.3792,-0.3969,-0.4367,-0.7186,-1.2056&daily=river_discharge&start_date=2024-10-20&end_date=2024-11-05&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
