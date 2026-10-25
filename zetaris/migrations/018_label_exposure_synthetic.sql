-- view: floodsense.exposure_join
-- columns: policy_id string, site_id string, lat double, lon double, in_footprint boolean, sum_insured_eur double, segment string, synthetic string
-- min_rows: 359
-- Replaces the select list of 014. Same 359-row synthetic book, with portfolio_synthetic.synthetic
-- kept (every row is yes). floodsense.exposure_join is not a live exposure feed. It reads
-- floodsense_seed_src, the same FILESTORE tables as floodsense_seed.exposure_join.
CREATE OR REPLACE SCHEMASTORE VIEW exposure_join WITH CONTAINER floodsense AS
SELECT
  p.policy_id,
  p.site_id,
  s.lat,
  s.lon,
  (s.in_flood_footprint = 'yes') AS in_footprint,
  CAST(p.sum_insured_eur AS DOUBLE) AS sum_insured_eur,
  s.site_type AS segment,
  p.synthetic AS synthetic
FROM floodsense_seed_src.portfolio_synthetic p
JOIN floodsense_seed_src.osm_sites s ON s.site_id = p.site_id
-- statement
-- view: floodsense_seed.exposure_join
-- columns: policy_id string, site_id string, lat double, lon double, in_footprint boolean, sum_insured_eur double, segment string, synthetic string
-- min_rows: 359
-- Replaces the select list of 016. Same columns as the floodsense container. Labelled synthetic.
CREATE OR REPLACE SCHEMASTORE VIEW exposure_join WITH CONTAINER floodsense_seed AS
SELECT
  p.policy_id,
  p.site_id,
  s.lat,
  s.lon,
  (s.in_flood_footprint = 'yes') AS in_footprint,
  CAST(p.sum_insured_eur AS DOUBLE) AS sum_insured_eur,
  s.site_type AS segment,
  p.synthetic AS synthetic
FROM floodsense_seed_src.portfolio_synthetic p
JOIN floodsense_seed_src.osm_sites s ON s.site_id = p.site_id
