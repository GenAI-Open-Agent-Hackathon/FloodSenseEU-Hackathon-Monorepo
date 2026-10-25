-- Live hourly rain for the eight Valencia points: last 3 days observed plus next 3 days forecast.
-- The archive API in 006 cannot serve the present, so this uses the forecast API (past_days keeps recent hours).
-- Table only, no view (see 030). Data: Open-Meteo, CC BY 4.0, free API non-commercial only.
CREATE LIGHTNING REST TABLE rain_live FROM OPENMETEO_FORECAST REQUEST (
  endpoint "https://api.open-meteo.com/v1/forecast?latitude=39.4278,39.4019,39.4267,39.4181,39.4244,39.1906,39.4694,39.5683&longitude=-0.4172,-0.4036,-0.3836,-0.3792,-0.3969,-0.4367,-0.7186,-1.2056&hourly=precipitation&past_days=3&forecast_days=3&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
