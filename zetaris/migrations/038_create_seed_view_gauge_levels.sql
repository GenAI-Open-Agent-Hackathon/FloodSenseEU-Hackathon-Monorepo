-- view: floodsense_seed.gauge_levels
-- columns: station string, water string, ts_utc timestamp, level_cm double, source string
-- min_rows: 6
-- Seed twin of 037. Same columns. No frozen PEGELONLINE extract is committed, so these
-- rows do not invent a centimetre reading. level_cm is NULL. source is seed:pegelonline,
-- which is how a seed row is told apart from a live pull.
-- Stations are the three gauges feeds.py pulls (BONN, KÖLN, KOBLENZ on the Rhine).
-- Timestamps are the window_from_utc values of EMSR773 and EMSR517 in
-- agents/floodsense_agents/events.py, written here as timestamps. One place owns the
-- event clock. This file only repeats it so the view can be built without Python.
-- Attribution, as a courtesy: Quelle: WSV, PEGELONLINE. The terms require no wording.
-- Licence DL-DE->Zero-2.0. docs/legal/sources.md.
CREATE OR REPLACE SCHEMASTORE VIEW gauge_levels WITH CONTAINER floodsense_seed AS
SELECT
  station,
  water,
  CAST(ts_utc AS TIMESTAMP) AS ts_utc,
  CAST(NULL AS DOUBLE) AS level_cm,
  source
FROM VALUES
  ('BONN', 'RHEIN', '2024-10-28 00:00:00', 'seed:pegelonline'),
  ('KÖLN', 'RHEIN', '2024-10-28 00:00:00', 'seed:pegelonline'),
  ('KOBLENZ', 'RHEIN', '2024-10-28 00:00:00', 'seed:pegelonline'),
  ('BONN', 'RHEIN', '2021-07-12 00:00:00', 'seed:pegelonline'),
  ('KÖLN', 'RHEIN', '2021-07-12 00:00:00', 'seed:pegelonline'),
  ('KOBLENZ', 'RHEIN', '2021-07-12 00:00:00', 'seed:pegelonline')
AS t(station, water, ts_utc, source)
