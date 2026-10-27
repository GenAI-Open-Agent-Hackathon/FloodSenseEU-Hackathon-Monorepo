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
| Open-Meteo flood, EU watch | REST table `eu_watch_live_v2` -> `floodsense.eu_watch` (migrations 063-065; 060-062 were the first cut) | 11 GloFAS points outside Germany (table below). Zetaris calls the API at query time (past 30 + 7 forecast days). Band = 7-day forecast max vs 2× (above) or 1.5× (near) the exact past-30-day median: a model band, not an official warning. Every discharge figure is a GloFAS model cell value, not a gauge reading. CC BY 4.0, `Weather data by Open-Meteo.com` |
| OSM Overpass | `ingestion/raw/live/osm_sites/live.csv` | Does not rewrite `prep/osm_sites.csv`. The 359-row portfolio join stays on that committed extract |

Not available: hochwasserzentralen.de (HTTP 200 with an empty body on 24 Oct 2026, including the documented calls)
and SAIH Júcar (web page only, no terms found).

Default `check` and `pull` skip `dwd`. PEGELONLINE is cleared in `docs/legal/sources.md` and is in `provenance.csv`. The DWD row remains in that CSV as a Hold record and is excluded from `floodsense.provenance` and `floodsense_seed.provenance`. Cached or replayed output must be labelled in the demo. The synthetic portfolio is labelled `synthetic=yes` on `exposure_join`.

Querying with the Zetaris CLI needs the login flags: `lightning-sql.sh --email admin@zetaris.com --password ...`.

### EU watch points: cell choice

Each point is a 0.05° GloFAS cell near the city. The check: the cell's 2013-2022 daily mean from the Open-Meteo Flood API (queried 27 Oct 2026, 3x3 cells around the city) against the long-term mean flow at the city as stated in the Wikipedia river articles (infobox or gauging-station figures; quoted from those articles, not re-measured by us, so treat them as approximate). The city-centre cell is often a side cell carrying about 1 m³/s, which is why cells move off the centre.

| Point | River / city | Cell (lat, lon) | GloFAS 2013-2022 mean | Reference long-term mean | Choice |
| --- | --- | --- | --- | --- | --- |
| EU01 | Seine / Paris | 48.925, 2.275 | 313 m³/s | ~310 m³/s (Paris) | kept |
| EU02 | Rhône / Lyon | 45.775, 4.825 | 591 m³/s | ~600 m³/s (Rhône at Lyon, above the Saône) | moved from 45.725, 4.775 (1222 m³/s, below the Saône confluence) |
| EU03 | Loire / Orléans | 47.875, 1.875 | 297 m³/s | ~350 m³/s (Orléans) | kept |
| EU04 | Po / Piacenza | 45.075, 9.625 | 886 m³/s | ~970 m³/s (Piacenza) | moved from 45.125, 9.725 (side cell) |
| EU05 | Ebro / Zaragoza | 41.625, -0.825 | 266 m³/s | ~230 m³/s (Zaragoza) | kept |
| EU06 | Vistula / Warsaw | 52.275, 20.975 | 481 m³/s | ~570 m³/s (Warsaw) | kept |
| EU07 | Danube / Vienna | 48.175, 16.475 | 1898 m³/s | ~1,920 m³/s (Vienna) | moved from 48.175, 16.425 |
| EU08 | Danube / Budapest | 47.475, 19.025 | 2482 m³/s | ~2,350 m³/s (Budapest) | kept |
| EU09 | Tisza / Szeged | 46.275, 20.125 | 660 m³/s | ~810 m³/s (Szeged) | kept |
| EU10 | Meuse / Liège | 50.675, 5.625 | 229 m³/s | ~250 m³/s (Liège) | moved from 50.675, 5.575 |
| EU11 | Vltava / Prague | 50.125, 14.375 | 139 m³/s | ~150 m³/s (Prague) | kept. Today's ~17-27 m³/s is autumn low flow, not an off-channel cell |
| — | Guadalquivir / Seville | best cell 37.325, -6.075 | 17 m³/s | ~160 m³/s (Seville / Alcalá del Río) | dropped: no cell near the city carries the main channel |
