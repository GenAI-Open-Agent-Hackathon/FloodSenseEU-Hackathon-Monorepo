# Zetaris migrations

Owner: Mihir (takeover 2026-10-25). File authors below are unchanged.

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
| `014_create_view_exposure_join.sql` | `floodsense.exposure_join` first create. Column list replaced by `018` | Urvashi |
| `015_create_view_provenance.sql` | `floodsense.provenance`: cleared datasets from `010`, DWD row excluded | Urvashi |
| `016_create_seed_view_exposure_join.sql` | `floodsense_seed.exposure_join` first create. Column list replaced by `018` | Urvashi |
| `017_create_seed_view_provenance.sql` | `floodsense_seed.provenance`, same query as 015 | Urvashi |
| `018_label_exposure_synthetic.sql` | Both exposure views keep `synthetic` (the book is not live) | Mihir |
| `030_create_rest_table_glofas_discharge_live.sql` | Rolling-window GloFAS REST table. No view | Saleeta |
| `031_create_lightning_db_openmeteo_forecast.sql` | Lightning database for the forecast rain REST table | Saleeta |
| `032_create_rest_table_rain_live.sql` | Rolling-window rain REST table. No view | Saleeta |
| `033_live_feed_tables.sql` | FILESTORE live tables except DWD. Header-only dirs are enough to create them | Saleeta |
| `034_create_view_hazard_now.sql` | `floodsense.hazard_now`: 007's columns over the rolling live tables. Column list replaced by `039` | Zain |
| `035_create_seed_view_hazard_now.sql` | `floodsense_seed.hazard_now`, the seed rows of 013. Column list replaced by `040` | Zain |
| `036_reregister_live_filestore.sql` | FILESTORE live tables again, new names, same paths, after the CSVs exist. No view | Mihir |
| `037_create_view_gauge_levels.sql` | `floodsense.gauge_levels` over `pegel_levels_staged` | Mihir |
| `038_create_seed_view_gauge_levels.sql` | `floodsense_seed.gauge_levels`. Stations only, no invented level | Mihir |
| `039_label_hazard_now_horizon.sql` | `floodsense.hazard_now` labels each hour `observed` or `forecast` | Mihir |
| `040_label_seed_hazard_now_horizon.sql` | `floodsense_seed.hazard_now` stays on 013 and is labelled `replay` | Mihir |
| `041_provenance_forecast_source.sql` | Both provenance views. Cleared count 8 after the forecast row | Mihir |
| `042_label_hazard_now_past.sql` | `floodsense.hazard_now` replaces 039's label: `past` or `forecast` | Mihir |
| `043_seed_gauge_levels_ahr.sql` | `floodsense_seed.gauge_levels` keeps the three Ahr Rhine gauges | Mihir |
| `044_register_pgvector_rag_chunks.sql` | JDBC datasource `PGVECTOR_RAG` and table `chunks`. Password stays `${PGVECTOR_PASSWORD}`. No view | Urvashi |

Rules (see [../README.md](../README.md)):

- Numbered, append-only, idempotent.
- Do not edit a file after it has been merged. Add the next number.
- No passwords, tokens, or cloud keys in SQL. Use `${VAR}` placeholders.
- Put a `-- statement` line between statements so the sync tool can send them one at a time.
- A migration that creates a view starts with `-- view: <container>.<view>`, `-- columns: <name> <type>, ...` and `-- min_rows: <n>`. `verify` checks the latest applied declaration of each view (a later file may `CREATE OR REPLACE` it). Every `floodsense.<view>` needs a `floodsense_seed.<view>` with the same columns, and `contracts/views.yaml` matches that latest declaration.
- Use `CREATE OR REPLACE SCHEMASTORE VIEW` for views and plain `CREATE` for everything else (no `IF NOT EXISTS` in Lightning SQL).
- The raw seed tables live in the database `floodsense_seed_src`, and the seed views in the container `floodsense_seed`. Do not give a table and a view the same name in one name space: the view hides the table and reads itself. (A database and a container may share a name only if the database is created first, which is why they do not.)

`py tasks.py zetaris-sync` applies pending files and then verifies declared views. For `--dry-run`, `status`, and `verify` on their own, run `python scripts/zetaris_sync.py` directly. Cold laptops stage seed CSVs and the live header files before `010`, `033`, and `036`. See [ingestion/prep/README.md](../../ingestion/prep/README.md).
