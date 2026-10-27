-- view: floodsense.weather_forecast
-- columns: point_id string, kind string, name string, river string, lat double, lon double, lead_h int, ts_utc timestamp, precip_mm double, model string, source string
-- min_rows: 3240
-- One row per watched place and forecast hour: 45 places x 72 hours, read from 070 on every query.
-- lead_h is the hour's position in the forecast (0 = the current GMT hour), so the next 48 hours
-- are lead_h < 48 without a clock in the SQL. precip_mm is the hourly precipitation sum (rain,
-- showers, snow water equivalent) of the hour ending at ts_utc, as Open-Meteo returns it.
-- kind: gauge (PEGELONLINE station; the agents map point_id to gauge_levels.station), eu
-- (eu_watch point) or valencia (hazard_now point). Names are ASCII on purpose (049 showed non-ASCII
-- literals can arrive double-encoded).
-- Data: Open-Meteo forecast API, CC BY 4.0, free API non-commercial only; model DWD ICON
-- (Deutscher Wetterdienst). Model output, not an official warning.
CREATE OR REPLACE SCHEMASTORE VIEW weather_forecast WITH CONTAINER floodsense AS
SELECT
  p.point_id,
  p.kind,
  p.name,
  p.river,
  CAST(p.lat AS DOUBLE) AS lat,
  CAST(p.lon AS DOUBLE) AS lon,
  CAST(h.lead_h AS INT) AS lead_h,
  h.ts_utc,
  h.precip_mm,
  'DWD ICON (icon_seamless) via Open-Meteo' AS model,
  'Open-Meteo forecast API (DWD ICON)' AS source
FROM VALUES
  (0, 'PEG01', 'gauge', 'MAXAU', 'RHEIN', 49.039, 8.3056),
  (1, 'PEG02', 'gauge', 'MAINZ', 'RHEIN', 50.004, 8.2753),
  (2, 'PEG03', 'gauge', 'KAUB', 'RHEIN', 50.0854, 7.765),
  (3, 'PEG04', 'gauge', 'KOBLENZ', 'RHEIN', 50.3586, 7.6047),
  (4, 'PEG05', 'gauge', 'ANDERNACH', 'RHEIN', 50.4434, 7.3921),
  (5, 'PEG06', 'gauge', 'BONN', 'RHEIN', 50.7364, 7.108),
  (6, 'PEG07', 'gauge', 'KOELN', 'RHEIN', 50.9369, 6.9633),
  (7, 'PEG08', 'gauge', 'DUESSELDORF', 'RHEIN', 51.2255, 6.7699),
  (8, 'PEG09', 'gauge', 'EMMERICH', 'RHEIN', 51.8293, 6.2456),
  (9, 'PEG10', 'gauge', 'Trier UP', 'MOSEL', 49.7322, 6.6269),
  (10, 'PEG11', 'gauge', 'Cochem', 'MOSEL', 50.1445, 7.1677),
  (11, 'PEG12', 'gauge', 'Fremersdorf', 'SAAR', 49.4089, 6.6484),
  (12, 'PEG13', 'gauge', 'FRANKFURT OSTHAFEN', 'MAIN', 50.1057, 8.715),
  (13, 'PEG14', 'gauge', 'WUERZBURG', 'MAIN', 49.7962, 9.926),
  (14, 'PEG15', 'gauge', 'Heidelberg UP', 'NECKAR', 49.4147, 8.7177),
  (15, 'PEG16', 'gauge', 'Lauffen', 'NECKAR', 49.0723, 9.1598),
  (16, 'PEG17', 'gauge', 'DRESDEN', 'ELBE', 51.0545, 13.7388),
  (17, 'PEG18', 'gauge', 'MAGDEBURG-STROMBRUECKE', 'ELBE', 52.1297, 11.6443),
  (18, 'PEG19', 'gauge', 'WITTENBERGE', 'ELBE', 52.9855, 11.7594),
  (19, 'PEG20', 'gauge', 'REGENSBURG EISERNE BRUECKE', 'DONAU', 49.0214, 12.1018),
  (20, 'PEG21', 'gauge', 'PASSAU DONAU', 'DONAU', 48.5761, 13.4591),
  (21, 'PEG22', 'gauge', 'FRANKFURT1 (ODER)', 'ODER', 52.3578, 14.5517),
  (22, 'PEG23', 'gauge', 'HOHENSAATEN-FINOW', 'ODER', 52.8647, 14.1411),
  (23, 'PEG24', 'gauge', 'HANN.MUENDEN', 'WESER', 51.4258, 9.6409),
  (24, 'PEG25', 'gauge', 'PORTA', 'WESER', 52.2487, 8.922),
  (25, 'PEG26', 'gauge', 'RHEINE UNTERSCHLEUSE', 'EMS', 52.288, 7.4341),
  (26, 'EU01', 'eu', 'Paris', 'Seine', 48.925, 2.275),
  (27, 'EU02', 'eu', 'Lyon', 'Rhone', 45.775, 4.825),
  (28, 'EU03', 'eu', 'Orleans', 'Loire', 47.875, 1.875),
  (29, 'EU04', 'eu', 'Piacenza', 'Po', 45.075, 9.625),
  (30, 'EU05', 'eu', 'Zaragoza', 'Ebro', 41.625, -0.825),
  (31, 'EU06', 'eu', 'Warsaw', 'Vistula', 52.275, 20.975),
  (32, 'EU07', 'eu', 'Vienna', 'Danube', 48.175, 16.475),
  (33, 'EU08', 'eu', 'Budapest', 'Danube', 47.475, 19.025),
  (34, 'EU09', 'eu', 'Szeged', 'Tisza', 46.275, 20.125),
  (35, 'EU10', 'eu', 'Liege', 'Meuse', 50.675, 5.625),
  (36, 'EU11', 'eu', 'Prague', 'Vltava', 50.125, 14.375),
  (37, 'VAL01', 'valencia', 'Paiporta', 'Barranc del Poyo', 39.4278, -0.4172),
  (38, 'VAL02', 'valencia', 'Catarroja', 'Horta Sud', 39.4019, -0.4036),
  (39, 'VAL03', 'valencia', 'Sedavi', 'Horta Sud', 39.4267, -0.3836),
  (40, 'VAL04', 'valencia', 'Alfafar', 'Horta Sud', 39.4181, -0.3792),
  (41, 'VAL05', 'valencia', 'Benetusser', 'Horta Sud', 39.4244, -0.3969),
  (42, 'VAL06', 'valencia', 'Algemesi', 'Jucar', 39.1906, -0.4367),
  (43, 'VAL07', 'valencia', 'Chiva', 'Barranc del Poyo', 39.4694, -0.7186),
  (44, 'VAL08', 'valencia', 'Utiel', 'Plana de Utiel', 39.5683, -1.2056)
AS p(loc, point_id, kind, name, river, lat, lon)
JOIN (
  SELECT
    COALESCE(f.location_id, 0) AS loc,
    t.pos AS lead_h,
    CAST(t.stamp AS TIMESTAMP) AS ts_utc,
    CAST(f.hourly.precipitation[t.pos] AS DOUBLE) AS precip_mm
  FROM OPENMETEO_FORECAST.weather_forecast_live f
  LATERAL VIEW posexplode(f.hourly.time) t AS pos, stamp
) h
  ON h.loc = p.loc
