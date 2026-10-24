# Live feeds

`feeds.py` checks every source and pulls current plus existing data. Stdlib only. Run from the repo root.

```text
python ingestion/feeds/feeds.py check
python ingestion/feeds/feeds.py pull --since 2024-10-20 --stage
python ingestion/feeds/feeds.py pull --only aemet,dwd --since 2021-07-10
python ingestion/feeds/feeds.py pull --stage --interval 900
```

`--stage` copies the CSVs into the local Zetaris volume (`.../shared/floodsense_live/<table>`). Migration
`033_live_feed_tables.sql` registers them as `floodsense_live_src.*`. Migrations 030-032 add two REST tables that
Zetaris fills by calling Open-Meteo at query time (rolling window, so always current).

| Source | Table | Notes |
| --- | --- | --- |
| Open-Meteo flood (GloFAS) | `discharge_daily` | history + 7-day forecast, `is_forecast` flag |
| Open-Meteo rain | `rain_hourly` | archive + forecast |
| Copernicus EMS | `ems_activations` | activation status for EMSR773 |
| AEMET | `aemet_daily` | 21 Valencia-province stations. Needs `AEMET_API_KEY` in `ingestion/.env`. 15 days per request |
| DWD via Brightsky | `dwd_rain_hourly` | four approximate Ahr valley points, for the July 2021 eval event |
| PEGELONLINE | `pegel_levels` | Rhine at Bonn, Köln, Koblenz, last 30 days |
| OSM Overpass | `prep/osm_sites.csv` | refreshes the existing sites table |

Not available: hochwasserzentralen.de (HTTP 200 with an empty body on 24 Oct 2026, including the documented calls)
and SAIH Júcar (web page only, no terms found).

Licences and attribution for DWD and PEGELONLINE are not yet recorded in `docs/legal/sources.md`, and their rows are
not yet in `provenance.csv`. Do that before citing them. Cached or replayed output must be labelled in the demo.

Querying with the Zetaris CLI needs the login flags: `lightning-sql.sh --email admin@zetaris.com --password ...`.
