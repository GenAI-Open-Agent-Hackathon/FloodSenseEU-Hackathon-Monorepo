-- view: floodsense_seed.hazard_now
-- columns: point_id string, ts_utc timestamp, rain_mm double, discharge_m3s double, warning_level string
-- min_rows: 576
-- The seed twin 034 owes the contract. It serves the frozen 28-30 Oct 2024 rows of 013, because a
-- machine with no live data has no present to report, and inventing one would be the lie the labelling
-- rules forbid. Callers that read floodsense_seed are already told the answer is a replay.
-- Reading 013 rather than repeating its VALUES keeps one copy of the seed rows: 013 stays the file to
-- regenerate, and the columns cannot drift apart.
CREATE OR REPLACE SCHEMASTORE VIEW hazard_now WITH CONTAINER floodsense_seed AS
SELECT
  point_id,
  ts_utc,
  rain_mm,
  discharge_m3s,
  warning_level
FROM floodsense_seed.hazard_timeline
