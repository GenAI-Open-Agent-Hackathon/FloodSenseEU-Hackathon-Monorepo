-- view: floodsense_seed.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 7
-- Seed view, same query as 015. Seven cleared datasets. ds_dwd_brightsky stays in the CSV and is
-- excluded here while DWD terms are Hold (docs/legal/sources.md).
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense_seed AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
WHERE dataset_id <> 'ds_dwd_brightsky'
