-- view: floodsense.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 9
-- 073 replaces 041: the same cleared datasets, plus one inline row for the weather forecast of
-- 070-072 (Open-Meteo forecast API, DWD ICON model). The row is inline rather than a new line in
-- ingestion/prep/provenance.csv, so no laptop has to re-stage that file. fetched_at is the day
-- the terms were read (docs/legal/sources.md row 19). ds_dwd_brightsky stays filtered out.
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
WHERE dataset_id <> 'ds_dwd_brightsky'
UNION ALL
SELECT
  'Open-Meteo forecast API (DWD ICON precipitation)' AS dataset,
  'https://open-meteo.com/en/docs/dwd-api' AS source_url,
  'Open-Meteo.com; model by Deutscher Wetterdienst (DWD)' AS publisher,
  'CC BY 4.0 (free API non-commercial only); DWD data CC BY 4.0' AS licence,
  'Weather data by Open-Meteo.com, model DWD ICON' AS attribution,
  CAST('2026-10-27 00:00:00' AS TIMESTAMP) AS fetched_at
-- statement
-- view: floodsense_seed.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 9
-- Same query as the live view above, as 041 was for 017.
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense_seed AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
WHERE dataset_id <> 'ds_dwd_brightsky'
UNION ALL
SELECT
  'Open-Meteo forecast API (DWD ICON precipitation)' AS dataset,
  'https://open-meteo.com/en/docs/dwd-api' AS source_url,
  'Open-Meteo.com; model by Deutscher Wetterdienst (DWD)' AS publisher,
  'CC BY 4.0 (free API non-commercial only); DWD data CC BY 4.0' AS licence,
  'Weather data by Open-Meteo.com, model DWD ICON' AS attribution,
  CAST('2026-10-27 00:00:00' AS TIMESTAMP) AS fetched_at
