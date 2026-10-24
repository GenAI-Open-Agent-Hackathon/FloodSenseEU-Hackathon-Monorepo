-- view: floodsense_seed.provenance
-- columns: dataset string, source_url string, publisher string, licence string, attribution string, fetched_at timestamp
-- min_rows: 6
-- Seed view, same query as 015: one row per dataset with source URL, licence and attribution, for layer (b) citations
-- (6 datasets, including AEMET). Reads the table from 010. fetched_at is its accessed_at (a date) cast to
-- a timestamp: open question for Mihir and Saleeta. The licence text is Saleeta's, still to be confirmed.
CREATE OR REPLACE SCHEMASTORE VIEW provenance WITH CONTAINER floodsense_seed AS
SELECT dataset, source_url, publisher, licence, attribution, CAST(accessed_at AS TIMESTAMP) AS fetched_at
FROM floodsense_seed_src.provenance
