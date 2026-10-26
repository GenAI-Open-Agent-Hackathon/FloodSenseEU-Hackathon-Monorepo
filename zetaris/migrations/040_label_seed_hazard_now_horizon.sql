-- view: floodsense_seed.hazard_now
-- columns: point_id string, ts_utc timestamp, rain_mm double, discharge_m3s double, warning_level string, horizon string
-- min_rows: 576
-- Replaces the select list of 035 so the seed twin keeps 039's columns.
-- Why these rows: this view serves the frozen 28-30 Oct 2024 copy in 013
-- (floodsense_seed.hazard_timeline, 3 days x 24 hours x 8 points = 576). 013 is a modelled
-- archive extract of that event. It is not a reading of today, and it is not a forecast.
-- A machine on floodsense_seed has no live window to split into past hours and forecast hours.
-- This view does not call current_timestamp(). Doing so would relabel October 2024 as if it
-- were the rolling window 039 reads, which invents a present the labelling rules forbid.
-- Every seed row is horizon 'replay'. observed and forecast belong only to the live view.
-- Reading 013 rather than copying its VALUES keeps one copy of the seed rows. Regenerate 013,
-- not this file, when that extract changes.
CREATE OR REPLACE SCHEMASTORE VIEW hazard_now WITH CONTAINER floodsense_seed AS
SELECT
  point_id,
  ts_utc,
  rain_mm,
  discharge_m3s,
  warning_level,
  'replay' AS horizon
FROM floodsense_seed.hazard_timeline
