# Zetaris migrations

Owner: Urvashi.

| File | What it does | Owner |
| --- | --- | --- |
| `001_create_lightning_db_openmeteo_flood.sql` | Lightning database for the flood REST table | Urvashi |
| `002_create_schemastore_container_floodsense.sql` | Container for the live `floodsense.*` views | Urvashi |
| `003_create_rest_table_glofas_discharge.sql` | REST table over the Open-Meteo Flood API, VAL01–VAL08 in one request | Urvashi |
| `004_create_view_discharge_daily.sql` | `floodsense.discharge_daily` | Urvashi |
| `005_create_lightning_db_openmeteo_archive.sql` | Lightning database for the rain archive | Urvashi |
| `006_create_rest_table_rain_archive.sql` | REST table over the Open-Meteo archive API, hourly rain, same eight points | Urvashi |
| `007_create_view_hazard_timeline.sql` | `floodsense.hazard_timeline`: hourly rain joined to the day's discharge | Urvashi |
| `010_seed_sources.sql` | Lightning database `floodsense_seed_src` with five FILESTORE tables over the prep CSVs | Saleeta |
| `011_create_schemastore_container_floodsense_seed.sql` | Container for the `floodsense_seed.*` views | Urvashi |
| `012_create_seed_view_discharge_daily.sql` | `floodsense_seed.discharge_daily`, a frozen copy of 004's rows | Urvashi |
| `013_create_seed_view_hazard_timeline.sql` | `floodsense_seed.hazard_timeline`, a frozen copy of 28–30 Oct from 007 | Urvashi |
| `014_create_view_exposure_join.sql` | `floodsense.exposure_join`: policies joined to OSM sites, reads the `010` tables | Urvashi |
| `015_create_view_provenance.sql` | `floodsense.provenance`: one row per dataset, read from the `010` table | Urvashi |
| `016_create_seed_view_exposure_join.sql` | `floodsense_seed.exposure_join`, same query as 014 | Urvashi |
| `017_create_seed_view_provenance.sql` | `floodsense_seed.provenance`, same query as 015 | Urvashi |

Rules (see [../README.md](../README.md)):

- Numbered, append-only, idempotent.
- Do not edit a file after it has been merged. Add the next number.
- No passwords, tokens, or cloud keys in SQL. Use `${VAR}` placeholders.
- Put a `-- statement` line between statements so the sync tool can send them one at a time.
- A migration that creates a view starts with `-- view: <container>.<view>`, `-- columns: <name> <type>, ...` and `-- min_rows: <n>`. `verify` checks the live view against these lines. Every `floodsense.<view>` needs a `floodsense_seed.<view>` with the same columns, and `contracts/views.yaml` is the reference.
- Use `CREATE OR REPLACE SCHEMASTORE VIEW` for views and plain `CREATE` for everything else (no `IF NOT EXISTS` in Lightning SQL).
- The raw seed tables live in the database `floodsense_seed_src`, and the seed views in the container `floodsense_seed`. Do not give a table and a view the same name in one name space: the view hides the table and reads itself. (A database and a container may share a name only if the database is created first, which is why they do not.)

`py tasks.py zetaris-sync` applies pending files. For the other forms (`--dry-run`, `status`, `verify`) run `python scripts/zetaris_sync.py` directly.
