-- view: floodsense.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 8
-- Same query as 015. The cleared count is now 8. provenance.csv gained ds_open_meteo_forecast
-- for the rolling rain and discharge behind hazard_now (032 and 030). ds_dwd_brightsky stays
-- in the CSV and is still filtered out while DWD is Hold. docker cp overwrites the staged
-- seed file, so running stage_local_zetaris.py again replaces provenance.csv. Only the live
-- header files are skip-if-present.
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
WHERE dataset_id <> 'ds_dwd_brightsky'
-- statement
-- view: floodsense_seed.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 8
-- Same query as 017, with the cleared count from the forecast row. DWD stays excluded.
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense_seed AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
WHERE dataset_id <> 'ds_dwd_brightsky'
