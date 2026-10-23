# Ingestion

Purpose: fetch and stage the datasets the agent will cite — Copernicus EMS footprints, OpenStreetMap site extracts, the synthetic insurer portfolio, and seed rows — plus the data README and licence notes that go with them.

Owner: Saleeta (prep, seed data, lineage) and Urvashi (Zetaris sources and any ingestion issue during the hackathon).

Zetaris objects are not created from this folder. Numbered SQL migrations live in [`zetaris/migrations/`](../zetaris/migrations/) and are applied with `python tasks.py zetaris-sync` (stub today; on Windows, `py tasks.py zetaris-sync`). Keep credentials in a local `ingestion/.env`. `python tasks.py init-env` copies `.env.example` to `.env` when the copy is missing and does not overwrite it. That file is the host-side Zetaris env (`127.0.0.1`). `agents/.env` is for containers and uses `host.docker.internal`. SQL that needs a secret uses a `${VAR}` placeholder, never a literal.

Put downloads (EMS rasters, OSM extracts, archives) in `raw/` or `data/`. Those paths are git-ignored. Do not commit them.

Terms for every source are recorded later in `docs/legal/sources.md` (not in this skeleton). Anything we cannot clear stays pointer-only. See [docs/GAMEPLAN.md](../docs/GAMEPLAN.md).

## Live gauges

PEGELONLINE polling lives in [`live/`](live/README.md). It writes `live.gauge_station` and `live.gauge_measurement` and does not create Zetaris objects. The Zetaris registration is [`zetaris/migrations/020_live_gauges.sql`](../zetaris/migrations/020_live_gauges.sql). LANUK NRW is out of scope until its portal licence is verified. Attribution for PEGELONLINE is in the live README and should be copied into `docs/legal/sources.md` when that file exists. Do not add that file on this branch.
