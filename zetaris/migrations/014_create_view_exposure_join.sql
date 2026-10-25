-- view: floodsense.exposure_join
-- columns: policy_id string, site_id string, lat double, lon double, in_footprint boolean, sum_insured_eur double, segment string
-- min_rows: 359
-- Synthetic policies (359) joined to OSM sites. in_footprint comes from osm_sites.in_flood_footprint,
-- computed in Python against the EMSR773 footprint (Zetaris has no ST_Contains). segment is the OSM
-- site_type: the contract's segment has no source column yet, open question for Mihir.
-- Checked on a scratch copy of the tables: 359 rows, 91 in the footprint (EUR 313.2 m insured),
-- 64 flood-covered policies in the footprint (EUR 216,138,000), matching ingestion/prep/README.md.
CREATE OR REPLACE SCHEMASTORE VIEW exposure_join WITH CONTAINER floodsense AS
SELECT
  p.policy_id,
  p.site_id,
  s.lat,
  s.lon,
  (s.in_flood_footprint = 'yes') AS in_footprint,
  CAST(p.sum_insured_eur AS DOUBLE) AS sum_insured_eur,
  s.site_type AS segment
FROM floodsense_seed_src.portfolio_synthetic p
JOIN floodsense_seed_src.osm_sites s ON s.site_id = p.site_id
