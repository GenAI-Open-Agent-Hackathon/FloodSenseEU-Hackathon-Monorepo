-- One REST table over the Open-Meteo archive API: hourly precipitation, all eight Valencia points in one request.
-- Same point order as 003: 0 VAL01  1 VAL02  2 VAL03  3 VAL04  4 VAL05  5 VAL06  6 VAL07  7 VAL08
-- (rows of ingestion/prep/valencia_points.csv). Zetaris adds location_id in request order; Open-Meteo
-- leaves it out for the first point, so it arrives as NULL there. The view in 007 handles that.
-- Window: 2024-10-20 to 2024-11-05, hours in UTC (timezone=GMT), same days as the discharge table.
-- Data: Open-Meteo historical weather API, CC BY 4.0. Attribution is in the provenance view.
-- Changing a REST table needs a new migration (no OR REPLACE for REST tables).
CREATE LIGHTNING REST TABLE rain_archive FROM OPENMETEO_ARCHIVE REQUEST (
  endpoint "https://archive-api.open-meteo.com/v1/archive?latitude=39.4278,39.4019,39.4267,39.4181,39.4244,39.1906,39.4694,39.5683&longitude=-0.4172,-0.4036,-0.3836,-0.3792,-0.3969,-0.4367,-0.7186,-1.2056&hourly=precipitation&start_date=2024-10-20&end_date=2024-11-05&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
