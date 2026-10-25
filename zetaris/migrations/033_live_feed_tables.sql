-- Live feed tables (Saleeta): FILESTORE pointers over CSVs written by ingestion/feeds/feeds.py.
-- Local stack path: /home/zetaris/customer-data/shared/floodsense_live/<table>.
-- ingestion/prep/stage_local_zetaris.py creates a header-only live.csv in each directory so this
-- file can apply on a cold laptop. Those files are not observations. feeds.py pull --stage replaces
-- them when a source is actually pulled. No view, so no contracts/views.yaml entry yet.
-- DWD is not registered here while docs/legal/sources.md marks it Hold. No dwd_rain_hourly path.
CREATE LIGHTNING DATABASE floodsense_live_src DESCRIBE BY "FloodSense EU live feed tables - Open-Meteo, AEMET, PEGELONLINE, EMS" OPTIONS ();
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
CREATE LIGHTNING FILESTORE TABLE pegel_levels FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/pegel_levels", header "true", inferSchema "true");
