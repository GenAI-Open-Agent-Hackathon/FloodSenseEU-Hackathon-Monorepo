# Ingestion

Ahr 2021 (EMSR517 replay): `python ingestion/prep/ahr_hazard.py --migrations` fetches real Open-Meteo rain (ERA5) and GloFAS discharge for AHR01-AHR04 and renders seed migrations 045/046. See `prep/README.md`.

Purpose: fetch and stage the datasets the agent will cite — Copernicus EMS footprints, OpenStreetMap site extracts, the synthetic insurer portfolio, and seed rows — plus the data README and licence notes that go with them.

Owner: Mihir (primary, takeover 2026-10-25). Saleeta is secondary on prep, seed data, lineage, and the demo.

Zetaris objects are not created from this folder. Numbered SQL migrations live in [`zetaris/migrations/`](../zetaris/migrations/) and are applied with `python tasks.py zetaris-sync` (on Windows, `py tasks.py zetaris-sync`). That command applies pending files and then verifies declared views. Keep credentials in a local `ingestion/.env`. `python tasks.py init-env` copies `.env.example` to `.env` when the copy is missing and does not overwrite it. That file is the host-side Zetaris env (`127.0.0.1`). `agents/.env` is for containers and uses `host.docker.internal`. SQL that needs a secret uses a `${VAR}` placeholder, never a literal. A cold laptop stages the seed CSVs before migration 010. See [`prep/README.md`](prep/README.md).

Put downloads (EMS rasters, OSM extracts, archives) in `raw/` or `data/`. Those paths are git-ignored. Do not commit them.

Terms for every source are recorded in `docs/legal/sources.md`. Prep tables and lineage are in `prep/README.md`. Anything we cannot clear stays pointer-only. See [docs/GAMEPLAN.md](../docs/GAMEPLAN.md).
