# Live feeds

`feeds.py` checks every source and pulls current plus existing data. Stdlib only. Run from the repo root.

```text
python ingestion/feeds/feeds.py check
python ingestion/feeds/feeds.py pull --since 2024-10-20 --stage
python ingestion/feeds/feeds.py pull --only aemet,dwd --since 2021-07-10
python ingestion/feeds/feeds.py pull --stage --interval 900
```

`--stage` copies the CSVs into the local Zetaris volume (`.../shared/floodsense_live/<table>`). Migration
`033_live_feed_tables.sql` registered those directories before the files existed, so those table names
answer `COUNT(*)` and fail a named column. `DROP` was refused. `036_reregister_live_filestore.sql`
registers `*_staged` on the same paths after the CSVs are in place. `floodsense.gauge_levels` reads
`pegel_levels_staged`. Migrations 030-032 add two REST tables that Zetaris fills by calling Open-Meteo
at query time (rolling window, so always current). `hazard_now` labels each of those hours `past`
or `forecast`. `past` is model output from `past_days` and GloFAS, not a station measurement.

| Source | Table | Notes |
| --- | --- | --- |
| Open-Meteo flood (GloFAS) | `discharge_daily` | history + 7-day forecast, `is_forecast` flag |
| Open-Meteo rain | `rain_hourly` | archive + forecast |
| Copernicus EMS | `ems_activations` | activation status for EMSR773 |
| AEMET | `aemet_daily` | 21 Valencia-province stations. Needs `AEMET_API_KEY` in `ingestion/.env`. 15 days per request |
| DWD via Bright Sky | `ingestion/raw/live/dwd_rain_hourly` | **Hold.** Not in the default pull and not registered by migration `033`. `--only dwd` stores a CSV locally. Do not cite it. Terms: `docs/legal/sources.md` |
| PEGELONLINE | `pegel_levels` | Rhine at Bonn, Köln, Koblenz, last 30 days. Terms read (DL-DE->Zero-2.0). Zetaris name after 036 is `pegel_levels_staged`. View `floodsense.gauge_levels`. Attribution `Quelle: WSV, PEGELONLINE` |
| PEGELONLINE now (`pegel_poll.py`) | `pegel_now_src` -> `floodsense.gauge_levels` | `python tasks.py pegel-poll` (add `--interval 600` to repeat). 26 stations on ten federal waterways, each with MW and MHW (checked against the REST API on 27 Oct 2026): Rhine: Maxau, Mainz, Kaub, Koblenz, Andernach, Bonn, Köln, Düsseldorf, Emmerich; Mosel: Trier UP, Cochem; Saar: Fremersdorf; Main: Frankfurt Osthafen, Würzburg; Neckar: Heidelberg UP, Lauffen; Elbe: Dresden, Magdeburg-Strombrücke, Wittenberge; Danube (Donau): Regensburg Eiserne Brücke, Passau Donau; Oder: Frankfurt1 (Oder), Hohensaaten-Finow; Weser: Hann. Münden, Porta; Ems: Rheine Unterschleuse. Band is the level against the station's MHW (official characteristic value). Attribution `Quelle: WSV, PEGELONLINE` |
| Open-Meteo flood, EU watch | REST table `eu_watch_live` -> `floodsense.eu_watch` (migrations 060-062) | 12 GloFAS points outside Germany: Seine/Paris, Rhône/Lyon, Loire/Orléans, Po/Piacenza, Ebro/Zaragoza, Vistula/Warsaw, Danube/Vienna, Danube/Budapest, Tisza/Szeged, Meuse/Liège, Vltava/Prague, Guadalquivir/Seville. Zetaris calls the API at query time (past 30 + 7 forecast days). Each point is the 0.05° GloFAS river cell with the largest past-30-day median among the 3x3 cells around the city (the city-centre cell is often a side cell with ~1 m³/s). Band = 7-day forecast max vs 2× (above) or 1.5× (near) the past-30-day median: a model band, not an official warning. CC BY 4.0, `Weather data by Open-Meteo.com` |
| OSM Overpass | `ingestion/raw/live/osm_sites/live.csv` | Does not rewrite `prep/osm_sites.csv`. The 359-row portfolio join stays on that committed extract |

Not available: hochwasserzentralen.de (HTTP 200 with an empty body on 24 Oct 2026, including the documented calls)
and SAIH Júcar (web page only, no terms found).

Default `check` and `pull` skip `dwd`. PEGELONLINE is cleared in `docs/legal/sources.md` and is in `provenance.csv`. The DWD row remains in that CSV as a Hold record and is excluded from `floodsense.provenance` and `floodsense_seed.provenance`. Cached or replayed output must be labelled in the demo. The synthetic portfolio is labelled `synthetic=yes` on `exposure_join`.

Querying with the Zetaris CLI needs the login flags: `lightning-sql.sh --email admin@zetaris.com --password ...`.
