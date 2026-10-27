-- Forecast lane: hourly precipitation for the next 72 hours at all 45 watched places in one
-- Open-Meteo forecast API request, DWD ICON model (models=icon_seamless: ICON-D2 ~2 km over
-- Germany, ICON-EU ~7 km over Europe, ICON global elsewhere, blended by Open-Meteo).
-- forecast_hours=72 starts at the current hour (GMT), so every query Zetaris runs re-fetches
-- the latest run and position 0 is the present hour. Nothing is stored.
-- Table only, in the Lightning database of 031. The view is floodsense.weather_forecast (071),
-- its seed twin floodsense_seed.weather_forecast (072).
-- Point order (location_id 0..44; Open-Meteo omits location_id for the first point):
--   0 PEG01 MAXAU, 1 PEG02 MAINZ, 2 PEG03 KAUB, 3 PEG04 KOBLENZ, 4 PEG05 ANDERNACH
--   5 PEG06 BONN, 6 PEG07 KOELN, 7 PEG08 DUESSELDORF, 8 PEG09 EMMERICH, 9 PEG10 Trier UP
--   10 PEG11 Cochem, 11 PEG12 Fremersdorf, 12 PEG13 FRANKFURT OSTHAFEN, 13 PEG14 WUERZBURG, 14 PEG15 Heidelberg UP
--   15 PEG16 Lauffen, 16 PEG17 DRESDEN, 17 PEG18 MAGDEBURG-STROMBRUECKE, 18 PEG19 WITTENBERGE, 19 PEG20 REGENSBURG EISERNE BRUECKE
--   20 PEG21 PASSAU DONAU, 21 PEG22 FRANKFURT1 (ODER), 22 PEG23 HOHENSAATEN-FINOW, 23 PEG24 HANN.MUENDEN, 24 PEG25 PORTA
--   25 PEG26 RHEINE UNTERSCHLEUSE, 26 EU01 Paris, 27 EU02 Lyon, 28 EU03 Orleans, 29 EU04 Piacenza
--   30 EU05 Zaragoza, 31 EU06 Warsaw, 32 EU07 Vienna, 33 EU08 Budapest, 34 EU09 Szeged
--   35 EU10 Liege, 36 EU11 Prague, 37 VAL01 Paiporta, 38 VAL02 Catarroja, 39 VAL03 Sedavi
--   40 VAL04 Alfafar, 41 VAL05 Benetusser, 42 VAL06 Algemesi, 43 VAL07 Chiva, 44 VAL08 Utiel
-- Gauges PEG01-PEG26 are the PEGELONLINE stations of ingestion/feeds/pegel_poll.py in that order
-- (positions from gauge_levels), EU01-EU11 the cells of 063, VAL01-VAL08 valencia_points.csv.
-- The same tuple is agents/floodsense_agents/watch.py FORECAST_POINTS; a test keeps them equal.
-- Numbers start at 070 to leave room for parallel branches.
-- Data: Open-Meteo forecast API, CC BY 4.0, free API non-commercial only. Model DWD ICON
-- (Deutscher Wetterdienst, CC BY 4.0). Attribution "Weather data by Open-Meteo.com, model DWD
-- ICON" (docs/legal/sources.md row 19). Model output, not an observation and not a warning.
CREATE LIGHTNING REST TABLE weather_forecast_live FROM OPENMETEO_FORECAST REQUEST (
  endpoint "https://api.open-meteo.com/v1/forecast?latitude=49.039,50.004,50.0854,50.3586,50.4434,50.7364,50.9369,51.2255,51.8293,49.7322,50.1445,49.4089,50.1057,49.7962,49.4147,49.0723,51.0545,52.1297,52.9855,49.0214,48.5761,52.3578,52.8647,51.4258,52.2487,52.288,48.925,45.775,47.875,45.075,41.625,52.275,48.175,47.475,46.275,50.675,50.125,39.4278,39.4019,39.4267,39.4181,39.4244,39.1906,39.4694,39.5683&longitude=8.3056,8.2753,7.765,7.6047,7.3921,7.108,6.9633,6.7699,6.2456,6.6269,7.1677,6.6484,8.715,9.926,8.7177,9.1598,13.7388,11.6443,11.7594,12.1018,13.4591,14.5517,14.1411,9.6409,8.922,7.4341,2.275,4.825,1.875,9.625,-0.825,20.975,16.475,19.025,20.125,5.625,14.375,-0.4172,-0.4036,-0.3836,-0.3792,-0.3969,-0.4367,-0.7186,-1.2056&hourly=precipitation&models=icon_seamless&forecast_hours=72&timezone=GMT",
  method "get",
  response_type "json",
  http_encoding "URLENCODED"
) HEADER () BODY ()
