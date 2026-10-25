-- Re-register the FILESTORE tables from 033 under new names.
-- 033 ran before /home/zetaris/customer-data/shared/floodsense_live/<table> held a CSV, so
-- inferSchema never saw a header. Those tables still answer COUNT(*). A named column or
-- SELECT * fails. REFRESH TABLE does not infer again. DROP TABLE, DROP VIEW and
-- DROP LIGHTNING FILESTORE TABLE were refused, so the 033 names stay as they are.
-- Stage the directories first (ingestion/prep/stage_local_zetaris.py, or feeds.py pull --stage).
-- This file then CREATE-s new names on the same paths. It does not drop anything, and it
-- does not create the database: floodsense_live_src already exists from 033.
-- No view in this file, so no -- view / -- columns / -- min_rows header. The gauge view is 037.
-- DWD stays unregistered while docs/legal/sources.md marks it Hold.
-- Applying this file before the CSVs exist breaks the new names the same way, and they
-- cannot be dropped either.
CREATE LIGHTNING FILESTORE TABLE discharge_daily_staged FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/discharge_daily", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE rain_hourly_staged FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/rain_hourly", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE ems_activations_staged FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/ems_activations", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE aemet_daily_staged FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/aemet_daily", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE pegel_levels_staged FROM floodsense_live_src
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_live/pegel_levels", header "true", inferSchema "true");
