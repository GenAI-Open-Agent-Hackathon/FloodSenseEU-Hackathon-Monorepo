# Handover: FloodSense EU (Open Agent Hackathon 2026, Track 02)

Written 27 Oct 2026, updated 28 Oct 2026 after submission. **Submitted:** the hackathon form (demo video, deck, repository link,
sponsor write-up) went in before the hard close. The repository is public. The submitted version is tag `v1.0.1`
([release notes](RELEASE-NOTES-v1.0.1.md)); `main` is ahead of the tag with the Nebius port and UI work (see the draft [v2.0.0 notes](RELEASE-NOTES-v2.0.0.md)). Read this first, then `README.md`,
`agents/README.md`, `ui/README.md` and `CHANGELOG.md`.

## What the product is

Explainable flood risk for Europe, with three desks: **Citizen**, **Insurer** (the payer), and
**Civil protection / Operator** (the founder's story: hotline staff are not flood experts). Every sentence cites its
source. A person approves anything outbound. Rubric: Impact 30, Technical 20, Innovation 15, Demo 15, Product & UX 10,
Sponsor tech 10 (Zetaris, Meterless Nightshift / H-MEM / World Model, NVIDIA Nemotron, Cursor).

## Architecture in one screen

- **Router** picks a lane per message (`agents/floodsense_agents/router.py`, `front_door.py`):
  - `reply`: greetings, help, thanks, off-topic. Fixed templates, instant.
  - `quick`: live level questions. Reads Zetaris views, deterministic cited claims, deterministic Judge. No model writes the answer, ~1 s.
  - `forecast`: "next 48 h / this week" for the 45 watched places. DWD ICON rain (Open-Meteo) + GloFAS + gauges + past
    pattern + H-MEM. No model writes the answer, 1-4 s.
  - `full`: Scope, Watchers, Memory (H-MEM), Investigator and Skeptic loop, Exposure, Playbook, Judge repair loop, human
    approval. About 5-6 min on Nightshift. Explicit `event_id`, `replay_ts` or a `doc_query` different from the question
    always go here, so the evals are stable.
- **Data**: everything is read through **Zetaris** views (`floodsense.gauge_levels`, `eu_watch`, `hazard_now`,
  `weather_forecast`, `exposure_join`, replay seeds). Migrations in `zetaris/migrations` (applied with
  `python tasks.py zetaris-sync`). 45 sources = 26 PEGELONLINE gauges + 11 GloFAS points + 8 Valencia demo points.
- **LLM**: default `LLM_BACKEND=nebius` (Token Factory, `NEBIUS_API_KEY`; fast `nvidia/Nemotron-3_5-Lightning`, deep `nvidia/Nemotron-3.5-Super-VL`). Verified live on 30 Oct with a real key (lane check and two full-lane replays only; no other path was run): lane check fast 1.1 s, deep 30.4 s; Ahr EMSR517 full lane 148 s, 12 calls, 44,569 tokens; Valencia EMSR773 281 s (concurrent), 14 calls, 40,370 tokens; every claim judged. `LLM_BACKEND=nightshift` keeps the **Nightshift** gateway (`:8088`, `meterless/fast` and `meterless/deep`).
  Rate limits (429): `agents/floodsense_agents/nightshift.py` has backoff, a concurrency cap and a pacer: 8 and 250 rpm on nebius (`NEBIUS_MAX_CONCURRENCY`, `NEBIUS_RPM`), 3 and 35 rpm on nightshift.
- **Memory**: H-MEM and World Model in `engines/` (`:8300`). Written only on approval. Demo seeds are labelled `demo-seed`.
- **RAG**: pgvector + NVIDIA NIM `nemotron-3.5-embed-1b`. 25 documents / 1,859 passages (`corpus/`, `scripts/rag_ingest.py`).
- **API** (`api/`, `:18000`): Redis cache, rate limits (10/min, 2 concurrent), SSE events, `GET /system`, `/watch/*` (Control tower),
  `GET /views/{name}` with a TTL and stale-if-error cache (`api/app/views_cache.py`).
- **Control tower** (`agents/floodsense_agents/tower.py`): rule-based watch loop, no model calls (`FF_WATCH_LOOP`, `WATCH_INTERVAL_S` 900);
  auto-assess is off by default (`FF_AUTO_ASSESS`), capped at 1 per hour and 3 per day, and never approves.
- **UI** (`ui/`, `:15173`): React/Vite. Run `cd ui && npm ci && npm test`.
- **Poller**: `pegel-poller` compose service refreshes PEGELONLINE every 10 min into Zetaris (mounts `docker.sock`, dev only).

## How to run everything (fresh clone)

1. `python tasks.py up-all` or `python3 tasks.py up-all`. Needs Docker Desktop and the separate Zetaris stack.
2. `python tasks.py zetaris-sync` to apply the Zetaris migrations.
3. Document ingest: `python tasks.py fetch-rag-corpus` then `python scripts/rag_ingest.py` (needs `PGVECTOR_DSN`, with the
   host port 15432 when run outside compose, and `NVIDIA_NIM_API_KEY`; use a venv that has `pypdf` and `psycopg`).
4. `python tasks.py demo-seed` (labelled demo memories and warmed cache). Set `FF_SEMANTIC_CACHE=true` in `api/.env` first.
5. Keys in `agents/.env`: `NEBIUS_API_KEY` (required with the default backend, else `LLM_BACKEND=nightshift`), `TAVILY_API_KEY` (optional, with `FF_TAVILY=true`), `NVIDIA_NIM_API_KEY` (embeddings). Hosted kit: `WATCH_ADMIN_TOKEN` (see `docs/DEPLOY-NEBIUS.md`). Lane check: `python tasks.py check-llm`.
6. Open http://127.0.0.1:15173. Env files (`agents/.env`, `api/.env`, `ingestion/.env`) are gitignored. Never commit keys.

Test suites (CI runs them): `python -m unittest discover -s tests` in `agents/`, `api/`, `contracts/`, `scripts/`;
`ruff check`; UI `npm test`, `npm run lint`, `npm run build`. Use a venv from `agents/requirements*.txt`; the system
Python on the main dev machine has a wrong langgraph.

## State at handover

Refreshed 30 Oct 2026. The submitted version is `v1.0.1`. `main` is ahead of it and a 2.0.0 is only drafted ([RELEASE-NOTES-v2.0.0.md](RELEASE-NOTES-v2.0.0.md), not released, no tag).

### On `main` since v1.0.1
Nebius Token Factory as default LLM backend (#109, #122), usage metering and lane check (#119), Tavily web evidence (#110, #118; unverified live), `GET /platform/status` (#113), hosted judge-demo kit (#117), Nebius submission pack and measurements (#116, #121), poller interval guard (#115), gauge band consistency (#114), UI: Token Factory tile and Platform strip (#123), Under the hood page (#126), goal and impact strips (#127), Review/Approvals fixes (#125), backend-aware wording (#124). Details: `CHANGELOG.md` [Unreleased].

### Open or held (not on main, 30 Oct)
- #108 MUI design system and 3D terrain gauge map (held).
- #111 local Postgres data backend, no Zetaris needed (held).
- #88 recorded-run UI walkthrough and #68 Skeptic one-view-per-statement: older teammate PRs, merge or close.
- #120 name the backend that served each model call (teammate).

Workflow used: branch, coding agent, independent review agent, review findings as PR comments, rework, CI green, merge, delete branch, update docs and CHANGELOG in every PR. `gh pr view --comments` fails with this token, so use `gh api repos/<owner>/<repo>/issues/<n>/comments`.

### Verified on the live stack
- The approve-and-remember loop: approving run `f6cc4adbc438` took the H-MEM count from 212 to 214 and the next Orléans forecast recalled the new memory (`mem-213`); this was observed on the demo machine on 27 Oct and is not stored as an artifact.
- Last end-to-end run on Nightshift: every claim cited and judged, 100% coverage on every scenario of the 27 Oct end-to-end run (the stored Nightshift eval evidence is the 4-item subset of that day). Quick lane about 1 s, forecast lane 1 to 4 s (no model writes the answer), full lane 5 to 6 minutes on Nemotron.
- 18 routes across the three desks (the main pages of each) were checked at 375 px with no horizontal scroll; the full navigation has 20 pages.

### Known bugs and weak spots
- First load of live pages took 5-10 s because the Zetaris views were cold. The cold latency is server side (a client prefetch did not help). The API now prewarms the views cache at startup and refreshes it in the background (`VIEWS_PREWARM_INTERVAL_S`, default 120 s, floor 30, 0 off). Not reproduced: the cold 5-10 s was not seen because the running API (an older build with the startup fill only) was already warm. Warm numbers only: `/views/gauge_levels` 0.49 s, then 0.06 s and 0.007 s; `/views/eu_watch` 0.005 s. Re-measure the cold case after a clean `up`.
- Insurer "Now" page is dense.
- Poller container tested only on Docker Desktop for Windows; `docker.sock` mount is dev-only.
- Tavily live call and the hosted Nebius VM kit are unverified (offline tests only).
- The `py` launcher may be broken on the dev machine; use `python tasks.py ...`.
- Open-Meteo free tier is non-commercial; one forecast question is about 45 calls.
- No flood-history documents/memories for Saar, Ems, Rhone, Ebro, Tisza.
- Full lane takes minutes and depends on NVIDIA rate limits. Quick/forecast/reply lanes do not.
- Answers are English only. A German/Spanish question gets an English answer with a note.
- Browser screenshots from the agent pane sometimes time out; read pages with `get_page_text`.

## Honesty rules (do not break)
No invented numbers or advice. Replays are labelled replays. GloFAS/model bands are amber "model, not an official warning",
never red. MHW is a long-term average, not a warning level. The synthetic portfolio is labelled synthetic. Demo seed
memories are labelled "demo seed". The Judge and the `cited_numbers` rules in `nodes/judge.py` are the integrity line.
A calm headline is allowed only when every checked status is Normal and data is complete.

## What remains for humans

Not done on purpose, and not done by the agents:

Done before and after submission:

- Licence: Apache-2.0 (`LICENSE`, copyright 2026 FloodSense EU contributors).
- Cursor wording in `README.md` ("How we built it") and `docs/SUBMISSION.md` states only what the repository records.
- Tags `v1.0.0` and `v1.0.1` with GitHub Releases. No `v1.0.0-rc.N` tag exists.
- Repository public; demo video, deck and the submission form are in.

Still open:

- Decide on the open pull requests #68, #88, #108, #111, #120 (merge or close) and whether to cut 2.0.0.
- Results are announced 6 Nov 2026. A correction to the submission form goes through the organisers (hackathons@genai.works); do not assume the form is still editable.
- The deck lives outside the repository. Death tolls on its slides should match `docs/DECK-FACTS.md` (the stored sources disagree in places).
- For any later live demo: set `FF_LIVE_DATA`, `FF_HMEM` and `FF_RAG_DOCS` to true in `agents/.env` (the examples ship them off) and recreate the agents container. Run `python tasks.py demo-seed` after a rebuild (set `FF_SEMANTIC_CACHE=true` in `api/.env` first), and walk every page in Live, Past and Demo modes once in a browser.

Rebuild command, if the stack must be recreated: `docker compose -p floodsense-app --project-directory . -f compose.yaml --profile rag --profile cache up -d --build agents api ui` (add `-f local/compose.console.yaml` only on the main dev machine, where that untracked file exists).
