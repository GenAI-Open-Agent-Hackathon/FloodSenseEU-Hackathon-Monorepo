# Prep data and lineage

Small, committable tables for the Valencia 2024 demo. Large downloads stay in `ingestion/raw/` (git-ignored). Owner: Saleeta, with Urvashi for anything that touches Zetaris.

## Files

| File | What it is | Made by | Source and licence |
| --- | --- | --- | --- |
| `valencia_points.csv` | 8 Valencia points checked against the EMSR773 footprint (`in_flood`, `dist_m_to_flood`) | `ems_footprint.py` | Copernicus EMS. Coordinates are approximate town centres |
| `ems_footprint.csv` | One row per EMSR773 layer: features, flooded hectares, bbox, download URL | `ems_footprint.py` | Copernicus EMS. Licence text to confirm |
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

## Where the seed rows live (proposal)

Zetaris cannot read files on a laptop. Proposal: put these CSVs in the S3 bucket named in `ingestion/.env` (`S3_*`) and register them as FILESTORE tables behind `floodsense_seed.*` views. The EMS footprint is already planned that way. This is a proposal until Urvashi confirms Lightning SQL FILESTORE support. Fallback: load the CSVs into the pgvector Postgres and register it as a JDBC source.

## Not done yet

- Seed view migrations in `zetaris/migrations/`. Waiting on Urvashi's check of the Lightning SQL syntax and on the S3 bucket.
- Loading `provenance.csv` into `floodsense.provenance`.
- AEMET observations. They need an API key.
- The EMS licence text (see `docs/legal/sources.md`).
