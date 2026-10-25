-- view: floodsense.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 7
-- Cleared citation rows only (7). The prep CSV also has ds_dwd_brightsky. DWD terms are Hold
-- (docs/legal/sources.md), so this view drops that row. min_rows is the cleared count.
-- Reads the table from 010. fetched_at is accessed_at cast to a timestamp.
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
WHERE dataset_id <> 'ds_dwd_brightsky'
