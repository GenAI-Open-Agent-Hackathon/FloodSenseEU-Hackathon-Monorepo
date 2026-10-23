# PEGELONLINE live gauges

Polls [PEGELONLINE](https://www.pegelonline.wsv.de/) REST API v2 and upserts
station metadata and water-level readings into Postgres (`live.gauge_station`,
`live.gauge_measurement`). Zetaris reads those tables over JDBC. One Bonn
station is also registered as a Lightning REST table so the native REST
connector is visible. Agents still read only through Zetaris.

Owner of this folder: Urvashi (ingestion). This change does not edit
`docs/GAMEPLAN.md` or the contract views.

## Run once

From the repo root, one command per line. PowerShell 5 has no `&&`.
Use `python`, not `py`.

```powershell
python tasks.py init-env
python tasks.py up-db
.\.venv\Scripts\python.exe -m pip install -r ingestion\live\requirements.txt
cd ingestion\live
..\..\.venv\Scripts\python.exe -m floodsense_live --once
cd ..\..
```

bash:

```bash
python3 tasks.py init-env
python3 tasks.py up-db
.venv/bin/python -m pip install -r ingestion/live/requirements.txt
cd ingestion/live
../../.venv/bin/python -m floodsense_live --once
cd ../..
```

Create the virtualenv first if `.venv` is missing (`python -m venv .venv` on
Windows, `python3 -m venv .venv` on macOS or Linux). `init-env` copies
`ingestion/live/.env.example` to `ingestion/live/.env` and does not overwrite
it. The Postgres password must match `pgvector/.env`. Both examples ship as
`local-dev-only`.

`up-db` starts only the existing pgvector service (compose profile `rag`) and
publishes `127.0.0.1:15432`. It does not start Zetaris, the API, or the UI.
`python tasks.py down` stops it and keeps the volume.

The first line of output looks like
`stations=6 measurements=... not_modified=0 requests=12`.
`measurements` counts upsert calls. The current reading is written again
after the history window, so a timestamp that is in both is counted twice
and stored once. A second `--once` in the same process reports `not_modified`
when PEGELONLINE returns 304. A new process has an empty ETag cache unless
Postgres already holds `live.gauge_http_cache`.

## Run continuously

The default interval is 900 seconds (15 minutes).

```powershell
cd ingestion\live
..\..\.venv\Scripts\python.exe -m floodsense_live
```

```bash
cd ingestion/live
../../.venv/bin/python -m floodsense_live
```

Ctrl+C stops the process. A failed cycle exits non-zero. `--dry-run` fetches
and parses but does not open Postgres.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `PEGELONLINE_BASE_URL` | the public v2 root | HTTPS only |
| `PEGELONLINE_STATIONS` | six Rhine gauges | Comma-separated shortnames |
| `PEGELONLINE_TIMESERIES` | `W` | Water level. `Q` is discharge |
| `PEGELONLINE_LOOKBACK` | `P1D` | ISO-8601 duration for history |
| `PEGELONLINE_INTERVAL_SECONDS` | `900` | Continuous mode. Minimum 60 |
| `PEGELONLINE_TIMEOUT_SECONDS` | `20` | Per request |
| `PEGELONLINE_MAX_RETRIES` | `3` | Extra attempts after the first |
| `PEGELONLINE_BACKOFF_SECONDS` | `1` | Doubles after each retry, cap 30s |
| `PEGELONLINE_REQUEST_PAUSE_SECONDS` | `0.25` | Pause between calls |
| `PEGELONLINE_ALL_CURRENT` | `0` | `1` fetches every station's current value and skips history |
| `PEGELONLINE_USER_AGENT` | FloodSenseEU poller | Sent on every request |
| `POSTGRES_HOST` | `127.0.0.1` | Host-side poller |
| `POSTGRES_PORT` | `15432` | Published pgvector port |
| `POSTGRES_DB` | `floodsense` | Same as `pgvector/.env` |
| `POSTGRES_USER` | `floodsense` | Same as `pgvector/.env` |
| `POSTGRES_PASSWORD` | example `local-dev-only` | Git-ignored copy only |
| `POSTGRES_SSLMODE` | `disable` | Local Docker socket |

`KOELN` is accepted as `KÖLN`. `DUESSELDORF` and `DUSSELDORF` are accepted as
`DÜSSELDORF`. The example file uses the ASCII aliases so PowerShell 5 does
not have to re-save it as UTF-16.

Default gauges, confirmed on PEGELONLINE on 2026-10-23, upstream to downstream:

| Shortname | UUID | Rhine km |
| --- | --- | --- |
| KAUB | `1d26e504-7f9e-480a-b52c-5932be6549ab` | 546.23 |
| KOBLENZ | `4c7d796a-39f2-4f26-97a9-3aad01713e29` | 591.49 |
| ANDERNACH | `5735892a-ec65-4b29-97c5-50939aa9584e` | 613.78 |
| BONN | `593647aa-9fea-43ec-a7d6-6476a76ae868` | 654.8 |
| KÖLN | `a6ee8177-107b-47dd-bcfd-30960ccc6e9c` | 688.0 |
| DÜSSELDORF | `8f7e5f92-1153-4f93-acba-ca48670c8ca9` | 744.2 |

## Postgres

Tables live in schema `live` on the pgvector service already in
`compose.yaml`. Host port `127.0.0.1:15432`, container port `5432`, database
`floodsense`. DDL is `sql/001_live_gauges.sql`. It is idempotent
(`IF NOT EXISTS`). The poller applies it on every run. Compose also mounts it
into `docker-entrypoint-initdb.d`, which runs only when the data volume is
empty. An existing volume does not replay that mount; the poller still does.

Primary key of `live.gauge_measurement` is `(station_uuid, timeseries, ts_utc)`.
`ts_utc` is UTC. Provenance columns on both tables: `source`, `source_url`,
`licence`, `fetched_at`.

`live.gauge_http_cache` stores ETags. It is not registered in Zetaris.

Check from PowerShell after `--once`:

```powershell
docker exec (docker ps -q -f name=floodsense-app-pgvector) psql -U floodsense -d floodsense -c "SELECT shortname, water_shortname, licence FROM live.gauge_station ORDER BY km"
```

```powershell
docker exec (docker ps -q -f name=floodsense-app-pgvector) psql -U floodsense -d floodsense -c "SELECT count(*) FROM live.gauge_measurement"
```

## Zetaris

Migration: [`zetaris/migrations/020_live_gauges.sql`](../../zetaris/migrations/020_live_gauges.sql).

**This SQL has not been executed against a live Zetaris.** Mihir verifies it
on his machine. `python tasks.py zetaris-sync` prints a TODO and sends
nothing, so the SQL editor is the path that works today.

1. Start Postgres and run the poller once, so the tables have rows.
2. Open the Zetaris SQL editor (UI `http://127.0.0.1:3000`).
3. Replace `${FLOODSENSE_PG_JDBC_URL}`, `${POSTGRES_USER}`, and
   `${POSTGRES_PASSWORD}` in the editor only. Put the same names in
   `ingestion/.env` for the day the sync tool learns to substitute them.
4. Run one statement at a time. Split on a line that is exactly `-- statement`.
5. If a CREATE says the object already exists, skip it. The view uses
   `CREATE OR REPLACE`. The command reference we followed has no
   `IF NOT EXISTS` for the datasource, the Lightning database, the REST
   table, or the SchemaStore container.

JDBC from a Zetaris container:

- Preferred: `docker network connect floodsense-app-net <zetaris-container>`
  then `jdbc:postgresql://pgvector:5432/floodsense?currentSchema=live`.
  List names with `docker ps --format "{{.Names}}"`. The DNS name is the
  compose service `pgvector`, not the generated container name.
- Docker Desktop on Windows alternative:
  `jdbc:postgresql://host.docker.internal:15432/floodsense?currentSchema=live`.
  The host port is bound to `127.0.0.1`. If that address is unreachable from
  the Zetaris container, use the network join. Do not publish port 15432 on
  the LAN.

Verify queries are the `SHOW` and `SELECT` statements in the migration.
The REST view is `floodsense_live.pegelonline_bonn_w`.

## Source terms

Record this in `docs/legal/sources.md` when that note exists. It is not in
this branch. Saleeta's `feat/ingestion-sources-terms` owns that file. Do not
add a second copy here.

- Source: PEGELONLINE, Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV).
- Portal: <https://www.pegelonline.wsv.de/>
- API: <https://pegelonline.wsv.de/webservices/rest-api/v2> (no authentication).
- Licence: DL-DE->Zero-2.0, <https://www.govdata.de/dl-de/zero-2.0>.
- Cadence: 15-minute values. On 2026-10-23 the `equidistance` field was `15`
  and `W` timestamps were 15 minutes apart. The JSON does not label the unit
  of `equidistance`. We store the integer as returned.
- Quality: `W` is `WASSERSTAND ROHDATEN` (water level, raw, unchecked), unit
  `cm` above gauge zero. Not a reviewed hydrological product.
- What we store: station metadata, the `W` series (history plus the current
  reading), provenance (`source`, `source_url`, `licence`, `fetched_at`).
  The public `voiceServiceNumber` is ignored.

### TODO: LANUK NRW is out of scope

The LANUK NRW high-water portal is not fetched. Its licence has not been
verified. Do not add it until someone records the portal terms in the legal
note. PEGELONLINE does not list Ahr gauges (Altenahr and the other 2021 Ahr
stations are not federal waterway gauges). ANDERNACH (Rhine km 613.78) is
upstream of the Ahr mouth and BONN (km 654.8) is downstream. Those two are
the Rhine pair in the default set. Ahr itself still needs a source whose
licence is known.

## Tests

`python tasks.py test` compiles this package and runs `ingestion/live/tests`.
Those tests use recorded fixtures and a scripted HTTP transport. They do not
call PEGELONLINE.

Upserts are checked on `InMemoryGaugeStore`, not on a Postgres container.
CI does not use Docker ([ADR 0008](../../docs/adr/0008-ci-runner-github-hosted.md)),
so a database service in GitHub Actions would not start. The memory store
uses the same primary keys. A null unit or state on a later row does not
erase a value already stored. `sql/001_live_gauges.sql` is the Postgres DDL
the poller applies; the test checks that text, it does not execute it.

## Decisions to confirm

- Postgres is the existing pgvector service, not a second database on 15432.
- The poller runs on the host and connects to `127.0.0.1:15432`.
- Zetaris is not added to `compose.yaml`. It may join `floodsense-app-net`.
- Default series is `W` only. `PEGELONLINE_ALL_CURRENT=1` replaces the station
  list with one current-value request per series and does not pull history.
- History rows do not include `stateMnwMhw` / `stateNswHsw`. A later history
  upsert keeps a state already stored. The current reading is written last
  so a new state still wins.
- ETags are stored only after the body has been upserted. A 304 updates the
  cache row and leaves measurements in place.
- ASCII aliases exist for `KÖLN` and `DÜSSELDORF`.
- Zetaris SQL follows the public command reference and the REST how-to
  (object payload, `LATERAL VIEW explode`, backtick-quoted mixed-case keys).
  It is untested on Mihir's Zetaris.
