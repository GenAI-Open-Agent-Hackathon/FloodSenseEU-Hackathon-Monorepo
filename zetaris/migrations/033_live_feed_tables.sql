-- Live feed tables (Saleeta): FILESTORE pointers over CSVs written by ingestion/feeds/feeds.py.
-- Local stack path: /home/zetaris/customer-data/shared/floodsense_live/<table>. Stage with: feeds.py pull --stage
-- Rows carry fetched_at and dataset_id (see floodsense.provenance). No view, so no contracts/views.yaml entry yet.
CREATE LIGHTNING DATABASE floodsense_live_src DESCRIBE BY "FloodSense EU live feed tables - Open-Meteo, AEMET, DWD, PEGELONLINE, EMS" OPTIONS ();
-- statement
CREATE LIGHTNING FILESTORE TABLE discharge_daily FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/discharge_daily", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE rain_hourly FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/rain_hourly", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE ems_activations FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/ems_activations", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE aemet_daily FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/aemet_daily", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE dwd_rain_hourly FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/dwd_rain_hourly", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE pegel_levels FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/pegel_levels", header "true", inferSchema "true");
