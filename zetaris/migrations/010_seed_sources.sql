-- Seed sources for the Valencia 2024 demo (Saleeta). Tables are FILESTORE pointers over CSVs
-- staged by ingestion/prep. Local stack path: /home/zetaris/customer-data/shared/floodsense_seed/<table>.
-- Provenance: ingestion/prep/provenance.csv. Licences: docs/legal/sources.md.

CREATE LIGHTNING DATABASE floodsense_seed DESCRIBE BY "FloodSense EU seed data - Valencia EMSR773" OPTIONS ();
-- statement
CREATE LIGHTNING FILESTORE TABLE ems_footprint FROM floodsense_seed
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_seed/ems_footprint", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE osm_sites FROM floodsense_seed
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_seed/osm_sites", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE portfolio_synthetic FROM floodsense_seed
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_seed/portfolio_synthetic", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE provenance FROM floodsense_seed
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_seed/provenance", header "true", inferSchema "true");
-- statement
CREATE LIGHTNING FILESTORE TABLE valencia_points FROM floodsense_seed
FORMAT csv
OPTIONS (path "file:///home/zetaris/customer-data/shared/floodsense_seed/valencia_points", header "true", inferSchema "true");
