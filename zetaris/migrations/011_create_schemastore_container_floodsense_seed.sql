-- SCHEMASTORE container for the floodsense_seed.* views: same view names and columns as floodsense.*.
-- The raw seed tables live in the Lightning database floodsense_seed_src (010), so the names do not clash.
-- If the container already exists, the sync tool skips this.
CREATE SCHEMASTORE CONTAINER floodsense_seed
