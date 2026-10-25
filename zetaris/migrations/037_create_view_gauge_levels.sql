-- view: floodsense.gauge_levels
-- columns: station string, water string, ts_utc timestamp, level_cm double, source string
-- min_rows: 0
-- Rhine water levels from PEGELONLINE, read from the table 036 registers after the CSV exists.
-- feeds.py writes station, water, time, level, unit, dataset_id, fetched_at. unit is cm.
-- This view names that value level_cm and keeps dataset_id as source (ds_pegelonline).
-- Attribution shown to a reader is the provenance row: Quelle: WSV, PEGELONLINE.
-- Licence DL-DE->Zero-2.0. docs/legal/sources.md.
-- min_rows is 0 because a cold start only has the header file from stage_local_zetaris.py.
-- That file is not an observation. feeds.py pull --stage replaces it. verify still checks
-- the column names, which is what the broken 033 table cannot answer.
-- No invented levels in this view. A header-only directory returns no rows.
CREATE OR REPLACE SCHEMASTORE VIEW gauge_levels WITH CONTAINER floodsense AS
SELECT
  station,
  water,
  CAST(time AS TIMESTAMP) AS ts_utc,
  CAST(level AS DOUBLE) AS level_cm,
  dataset_id AS source
FROM floodsense_live_src.pegel_levels_staged
