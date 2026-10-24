-- Live twin of 003: the same eight Valencia points, but a rolling window instead of the 2024 event days.
-- past_days=7 and forecast_days=7, so every query Zetaris runs re-fetches the current GloFAS discharge.
-- Table only, no view: a floodsense.* view needs a seed twin and an entry in contracts/views.yaml (Mihir).
-- Point order is the rows of ingestion/prep/valencia_points.csv (0 VAL01 ... 7 VAL08), as in 003.
-- Data: Open-Meteo Flood API, CC BY 4.0, free API non-commercial only. Not a cached or replayed source.
CREATE LIGHTNING REST TABLE glofas_discharge_live FROM OPENMETEO_FLOOD REQUEST (
  endpoint "https://flood-api.open-meteo.com/v1/flood?latitude=39.4278,39.4019,39.4267,39.4181,39.4244,39.1906,39.4694,39.5683&longitude=-0.4172,-0.4036,-0.3836,-0.3792,-0.3969,-0.4367,-0.7186,-1.2056&daily=river_discharge,river_discharge_mean,river_discharge_max&past_days=7&forecast_days=7&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
