# Prep data and lineage

Small, committable tables for the Valencia 2024 demo. Large downloads stay in `ingestion/raw/` (git-ignored). Owner: Mihir primary (takeover 2026-10-25). Saleeta is secondary on prep and the demo.

## Files

| File | What it is | Made by | Source and licence |
| --- | --- | --- | --- |
| `valencia_points.csv` | 8 Valencia points checked against the EMSR773 footprint (`in_flood`, `dist_m_to_flood`) | `ems_footprint.py` | Copernicus EMS. Coordinates are approximate town centres |
| `ems_footprint.csv` | One row per EMSR773 layer: features, flooded hectares, bbox, download URL | `ems_footprint.py` | Copernicus EMS. Terms read; citation wording to check |
| `osm_sites.csv` | 961 OSM sites (industrial, retail, school, health, emergency) in the Horta Sud bbox, tagged `in_flood_footprint` | `osm_sites.py` + `osm_query.overpassql` | OpenStreetMap, ODbL 1.0 |
| `portfolio_synthetic.csv` | 359 invented commercial-property policies on the industrial and retail sites | `synthetic_portfolio.py` (seed 773) | Generated. **Synthetic.** No personal data |
| `provenance.csv` | Dataset, source URL, licence, attribution, access date for each dataset | by hand | See `docs/legal/sources.md` |
| `eval_sources.md` | Draft source list for the evaluation set | by hand | n/a |

## Lineage

```text
Copernicus rapid-mapping API ──► raw/ems/*.zip ──► ems_footprint.py ──► ems_footprint.csv, valencia_points.csv
Overpass API (osm_query.overpassql) ──► raw/osm_valencia.json ──► osm_sites.py ──► osm_sites.csv
osm_sites.csv ──► synthetic_portfolio.py ──► portfolio_synthetic.csv
```

Rebuild from the repo root with the venv interpreter. The EMS zips come from the `source_url` column in `ems_footprint.csv` and go in `ingestion/raw/ems/<layer>/`. `shapely` is needed for the scripts (`pip install shapely`).

```powershell
.\.venv\Scripts\python.exe ingestion\prep\ems_footprint.py
.\.venv\Scripts\python.exe ingestion\prep\osm_sites.py
.\.venv\Scripts\python.exe ingestion\prep\synthetic_portfolio.py
```

## Headline numbers (for the demo and for checking views later)

- EMSR773 layers staged: AOI01 (Valencia province), AOI02 (Plana de Utiel), AOI03 (Horta Sud, DEL and GRA), AOI04 (Algemesí). Event 2024-10-29 14:30 UTC.
- Of the 8 points, 2 sit inside the delineated footprint (Paiporta, Alfafar). 5 are within about 60–320 m of it. Chiva is 2.7 km away and is kept as an upstream point.
- Synthetic portfolio: 359 policies. 91 sit inside the observed footprint (SUM insured about EUR 313 m). 64 of those have flood cover (about EUR 216 m).
- Delineation comes from satellite imagery. Dense urban areas can be under-detected, so "near the footprint" does not mean "dry".

## Cold laptop: stage CSVs, then sync

Zetaris cannot read files on the laptop. Migration `010_seed_sources.sql` creates the Lightning database `floodsense_seed_src` (not the `floodsense_seed` container) and one FILESTORE table per CSV. Each table path is a directory inside the Zetaris volume:

```text
file:///home/zetaris/customer-data/shared/floodsense_seed/<table>
```

`stage_local_zetaris.py` copies `<table>.csv` to `<table>/<table>.csv` in that directory. The default container name is `zetaris-driver-1`. Pass another name when `docker ps` shows one. The script stops if a CSV is missing or Docker cannot see the container.

From a fresh clone, with Zetaris already listening on `:8888`. No `AEMET_API_KEY`. Do not pull DWD.

```bash
cp ingestion/.env.example ingestion/.env
# Set ZETARIS_API_KEY in ingestion/.env. Leave AEMET_API_KEY empty.
python ingestion/prep/stage_local_zetaris.py
python tasks.py zetaris-sync
python scripts/zetaris_sync.py verify
```

```powershell
copy ingestion\.env.example ingestion\.env
.\.venv\Scripts\python.exe ingestion\prep\stage_local_zetaris.py
py tasks.py zetaris-sync
.\.venv\Scripts\python.exe scripts\zetaris_sync.py verify
```

`stage_local_zetaris.py` copies the seed CSVs and writes a header-only `live.csv` in each `floodsense_live/<table>` directory that migration `033` registers (`discharge_daily`, `rain_hourly`, `ems_activations`, `aemet_daily`, `pegel_levels`). It does not create `dwd_rain_hourly`. Those header files are placeholders so `033` can `CREATE`. They are not observations and no view selects them. The stage script does not overwrite a csv already in the container. `feeds.py pull --stage` copies that source's `live.csv` over the placeholder.

`zetaris-sync` applies pending migrations and then verifies declared views. A failure in a later file still verifies views already in the ledger, then exits non-zero. `sync --dry-run` sends nothing and does not verify.

Seed and contract views after that path:

- `floodsense_seed.discharge_daily` is the frozen 136-row window and does not need the network.
- `floodsense.exposure_join` and `floodsense_seed.exposure_join` are the same synthetic book (migration `018` keeps `synthetic`, value `yes` on all 359 rows). They read `floodsense_seed_src`, not a live book.
- `floodsense.provenance` and `floodsense_seed.provenance` return the 7 cleared datasets. `ds_dwd_brightsky` stays in `provenance.csv` and is filtered out of both views while DWD is Hold.

`floodsense.discharge_daily` (136) and `floodsense.hazard_timeline` (live `min_rows` 3264) still need Open-Meteo reachable from the laptop. They are not satisfied by the header-only live files.

Stage the seed CSVs before the first apply of `010`. A later "already exists" on that migration does not copy files that were never staged.

Checked on 23 Oct 2026 against the local platform package: row counts 5, 961, 359, and 8 for the footprint, sites, portfolio, and points. The provenance CSV has 8 rows; the views keep 7. The join of flood-covered synthetic policies with in-footprint sites returns 64 policies and EUR 216,138,000, the same as the Python check. Lightning rejects a `DESCRIBE BY` text that has parentheses; use letters, digits, `_ . - ,` and spaces only.

## Not in this folder yet

- AEMET observations. They need an API key (`AEMET_API_KEY` in `ingestion/.env.example`).
- The EMS Citation Guidelines wording (see `docs/legal/sources.md`).
