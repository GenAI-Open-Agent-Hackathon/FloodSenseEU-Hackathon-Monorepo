# FloodSense EU — team gameplan

Condensed from the team gameplan v2 (22 Oct 2026) for the Open Agent Hackathon 2026, Track 02: the agent that can explain why. This file is the shared playbook. It is a working plan, not a legal opinion.

Build window: Thu 22 Oct 00:00 UTC → Tue 27 Oct 23:45 UTC (Berlin: Thu 22 Oct 02:00 CEST → Wed 28 Oct 00:45 CET). Results 6 Nov.

Targets: demo freeze `v1.0.0-rc.1` Mon 26 Oct 20:00 CET · `v1.0.0` Tue 27 Oct ~14:00 CET · submission Tue 27 Oct 21:00 CET.

## What we are building

An agent team that watches European flood and weather data and explains why a place is at risk, with a cited causal chain (rain → catchment → river → site). A Skeptic tries to disprove each link. An LLM-as-a-Judge scores grounding before a human reviews the answer. The agents tell an insurer which policies and sites are exposed and what to do in the next 6–72 hours. A human approves every outbound action.

The demo replays the Valencia floods of 29 Oct 2024 (Copernicus EMS activation EMSR773) on public data federated through Zetaris. Every number on screen links to the query, the dataset, and the original source.

Mandatory stack: Zetaris (each person runs their own local Docker Compose), Meterless Nightshift (all LLM calls, NVIDIA Nemotron lanes), the Meterless engines in `engines/` (H-MEM and World Model), Cursor. The sidecar is in compose. H-MEM and the World Model are not load-bearing on main until Ayush #15 and #16 merge. Until then the agents keep `NoMemory` and do not call `ENGINES_URL`.

Our stack: Python and LangGraph (agents, human-in-the-loop), FastAPI, React with TSX on Vite, GitHub, docker compose for our app, optional pgvector and Redis. pgvector is stretch (citation layer (c)), not a v1 gate. GitHub Actions runs lint, tests, and secret scans on pull requests and on pushes to `main` ([adr/0008-ci-runner-github-hosted.md](adr/0008-ci-runner-github-hosted.md)).

## Customer and KPI

The primary customer is the insurer. The person in the demo is the analyst on the desk. The book of business is the synthetic portfolio (`ds_portfolio_syn` in `ingestion/prep/provenance.csv`), labelled synthetic, not real policies. The KPI we report is the hallucination rate on the eval set: the share of claims their own citations do not support. The proposal is ≤ 5%, with citation coverage at 100%. The metric table is under Evaluation set.

## Non-goals

A2A and MCP are out of this hackathon. Agents read through Zetaris and call models through Nightshift. We do not add an Agent-to-Agent protocol or an MCP server.

## How we want the demo to score

| Criterion | What we show |
| --- | --- |
| Impact | Insurer event-response console. Valencia replay. One business-model slide: insurers pay first; lenders, site operators, and reinsurers follow; citizens get it free. |
| Technical | Small tagged increments, contract tests, HITL tests, cache and rate limits, a C4 diagram and ADRs. |
| Innovation | Skeptic loop, Judge before the human, citations for layers (a) and (b). Layer (c) is stretch. H-MEM is not load-bearing until Ayush #15 and #16 merge. |
| Demo | A 3–4 minute script (Saleeta). Live when Nemotron is up. Labelled cached replay when it is not. Approval on screen. |
| Product | One screen: map, causal chain, Skeptic verdicts, Judge scores, evidence drawer, approve / edit / reject. |
| Sponsor tech | Every claim cites a Zetaris `queryId`. Every LLM call goes through Nightshift on pinned Nemotron lanes. The engines sidecar is in the tree. H-MEM and World Model are not load-bearing on main until Ayush #15 and #16 merge. |

Win line we hold ourselves to: grounded and cited answers, Zetaris as the only data path for agents, 100% of LLM calls through Nightshift, no outbound action without approval, and cached output always labelled.

## Team

Five peers. The Architect is one role among them, not a team lead. Scope changes are proposed by the area owner and agreed at stand-up. Pairs share a branch. Every feature has a builder and a reviewer from outside the pair. Path-level detail is in [OWNERSHIP.md](OWNERSHIP.md).

| Person | Role | Owns |
| --- | --- | --- |
| Mihir | Architect | Architecture, `docs/` and ADRs, CI/CD, security review, compose, contracts. Zetaris, ingestion, and live gauges (PEGELONLINE; takeover 2026-10-25). Judge with Zain. |
| Urvashi | Zetaris expertise | Remains on the team. Tracing and the citation pipeline with Saleeta and Mihir. |
| Saleeta | Ingestion, citations, story | Secondary on ingestion prep and the demo. Citation records, slide deck, video, and live script. |
| Ayush | Nightshift, memory, engines | Nightshift client, `meterless/fast` and `meterless/deep`, H-MEM, World Model, `engines/`, memory, embeddings research, semantic cache. |
| Zain | LangGraph, HITL, Judge, UI | Graph and nodes with Ayush, `interrupt()` and the checkpointer, the Judge with Mihir, then the UI. |

Pairs: Urvashi + Saleeta (data, then citations). Ayush + Zain (graph, then memory and HITL). Zain + Mihir (Judge, then UI). Urvashi + Saleeta + Mihir (document citations, behind a flag). Saleeta + everyone (deck and demo).

The citizen and insurer console is on main. Zain owns the UI path. Path detail is in [OWNERSHIP.md](OWNERSHIP.md).

## Phases

| Phase | When | Goal | Exit |
| --- | --- | --- | --- |
| P1 Foundations | Thu 22 – Fri 23 | Skeleton, contracts, first sources, agent graph on seeded views, Day-1 research and terms checks | `v0.4.0`: Investigator + Skeptic answer a real question with citations. Core sources federated on main. |
| P2 Integrate | Sat 24 | Everyone syncs. Agents switch to live views. UI v1 on the real API. | `v0.7.0`: UI shows layer (a) and (b) citations. Zain owns the UI path. That screen landed inside `v0.2.0`. |
| P3 Depth | Sun 25 – Mon 26 | HITL, Judge, memory, cache, eval set, demo script. Layer (c) document citations and hierarchical document chunks are stretch. | `v1.0.0-rc.1` demo freeze, Mon 26 Oct 20:00 CET. |
| P4 Ship | Tue 27 | Test the candidate, security review, tag, record, submit. | Submission sent by 21:00 CET. |

Slots are a guide (Berlin time, AM ≈ 09:30–14:00, PM ≈ 14:30–20:00). Thursday starts mid-afternoon because the clock started at 02:00 CEST. Clocks go back on Sunday 25 Oct at 03:00 (CEST → CET).

### Thursday

- Mihir: read-through, private repo, skeleton, then CI guardrails and contracts on the next branch, C4, tag `v0.0.0` only after those checks exist.
- Urvashi: Zetaris up, vector-search research, hazard view schemas, then migrations for Open-Meteo Flood / GloFAS and a discharge view, plus the sync ledger.
- Saleeta: pick 5–10 Valencia points on EMSR773, terms check with Urvashi, seed views, stage the EMS footprint.
- Ayush: Nightshift client, `/v1/models`, pinned lanes, whether embeddings are served. First node answers on seed views.
- Zain: LangGraph skeleton with Ayush, state and citation models, `run_sql` against a fake Zetaris, graph wiring.

### Friday

- Mihir: UI concept with mock data, ADR drafts, Judge rubric with Zain, reviews, tags.
- Urvashi: rain archive, `hazard_timeline`, `exposure_join`, sync dry-run, research written up.
- Saleeta: OSM sites, synthetic portfolio, EMS footprint table, provenance rows, eval-set source list.
- Ayush: World Model entities, engines sidecar, H-MEM scaffold.
- Zain: Watchers and Investigator, then the Skeptic loop (at most 3 SQL counter-checks) toward `v0.4.0`.

### Saturday (sync day)

Everyone pulls main, runs `python tasks.py zetaris-sync` (`py tasks.py zetaris-sync` on Windows), and runs our compose stack without touching Zetaris. Urvashi runs the Zetaris desk. Agents move to live views. Saleeta wires dataset → source citations. Ayush and Zain add Exposure and Playbook, then Zain starts HITL. UI v1 (`v0.7.0`) is Zain's path. The console Mihir landed is that screen, inside `v0.2.0`.

### Sunday and Monday

Zain finishes approve / edit / reject, builds the Judge with Mihir, then moves to the UI. Ayush adds long-term memory, short-term thread memory, the semantic cache, and a labelled replay drill. Urvashi, Saleeta, and Mihir add the eval set (Valencia 2024, then Ahr / NRW 2021). Hierarchical document chunks and layer (c) document citations are stretch. Monday 20:00 CET is the demo freeze. After that, only `fix/*` pull requests.

### Tuesday

Everyone tests the release candidate on their own area and one other. Mihir does the security review, tags `v1.0.0` around 14:00 CET, switches the repo to public, and submits by 21:00 CET. Saleeta records the video and finishes the deck. Ayush supplies sponsor-tech evidence. Urvashi checks licences and attributions in the UI and the README.

### Daily rhythm

- 09:30 stand-up (15 min, rotate the facilitator): blockers, today's increment, yesterday's tag.
- 14:00 optional pair check-in: contract changes are announced here.
- 19:30 merge window: green branches merge to main. Unfinished work goes in behind a feature flag. Nothing stays unmerged overnight.
- 20:00 increment demo (2 min each) and tag. Mihir creates the tag as CI/CD owner.
- After every pull of main: `python tasks.py zetaris-sync` before starting work. On Windows, `py tasks.py zetaris-sync`. One command per line. PowerShell 5.x has no `&&`.

## Increments

The plan was thirteen product increments, a release candidate, and the release. Each increment merges through a pull request and is demoed at 20:00. Tags are immutable. On the 0.x line they are `v0.MINOR.0` only. There is no `v0.MINOR.PATCH` tag and no `v0.x.y` fix tag. A fix lands on `main` and rides the next minor tag. `v1.0.0-rc.N` is the candidate series after the Monday freeze. A slipped increment merges behind its flag. The tag records what actually works. A docs change does not create a tag.

`v0.0.0` is the annotated skeleton tag on `eacf34c`. `v0.1.0` is the annotated data-slice tag on `7045fc5`. `v0.2.0` is the annotated live demo stack on `71390b6`: agents graph, insurer desk, engines sidecar, fast lane, and parallel Zetaris. `v0.3.0` is the annotated tag for live gauges and `hazard_now`. All four have GitHub Releases. Laptop Zetaris e2e for `v0.3.0` (stage, `zetaris-sync`, and verify on a machine with the engine) is deferred to the morning of 26 Oct 2026. The tag records the code on main after CI.

`v0.3.0` adds what was not in `v0.1.0`. [#28](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/28) is the live gauge views and the FILESTORE re-registration. [#24](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/24) is `floodsense.hazard_now` and its seed twin, migrations `034` and `035`. [#29](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/29) is the should-fixes: migration `042` labels each rolling hour `past` or `forecast`, and migration `043` keeps the seed gauge rows to the three Ahr Rhine gauges (Bonn, Köln, Koblenz) with no invented level. [#26](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/26) is the `v0.MINOR.0` tag policy. [#27](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/27) accepts lane names on judge `model_id`. Core sources, provenance, `ingestion/feeds/`, and the `pegel_levels` table in migration `033` already shipped in `v0.1.0`. Built: Urvashi, Saleeta. `hazard_now`: Zain. Owner now: Mihir (takeover 2026-10-25).

After `v0.3.0`, the next product tag is `v0.9.0` once Ayush #15 and #16 are load-bearing. If that work is still open at the Monday freeze, the next tag is `v1.0.0-rc.1` (Mon 26 Oct 20:00 CET). `v0.4.0`, `v0.5.0`, `v0.6.0`, `v0.7.0`, `v0.8.0`, and `v0.10.0` already shipped inside `v0.2.0` and stay there. `v0.11.0` is stretch. `v0.12.0` is not in this tree. The 0.x line stays `v0.MINOR.0` only.

`v0.2.0` includes the Nightshift check, the `engines/` sidecar, the citizen and insurer console, and from #4 the LangGraph graph, the HITL interrupt, the Judge, the API run proxy, and `evals/`. These planned rows shipped early inside that tag, so they are not tags of their own:

- `v0.4.0` — Watchers → Investigator → Skeptic, at most 3 rounds. The World Model board is not in the graph.
- `v0.5.0` — FastAPI runs and SSE, and the compose stack. `FF_LIVE_DATA` selects `floodsense.*`.
- `v0.6.0` — Deterministic exposure SQL, and playbook actions that cite claim ids.
- `v0.7.0` — UI v1 (map, chain, evidence drawer, layers (a) and (b)). Zain owns the UI path. Content: Saleeta. Mihir landed the console.
- `v0.8.0` — `interrupt()`, the SQLite checkpointer, and the approval API.
- `v0.10.0` — Judge scores on the approval payload.

`v0.9.0` did not ship as a load-bearing increment. H-MEM and the World Model are not load-bearing on main until Ayush #15 and #16 merge. The agents package does not call `engines/` yet. `FF_HMEM` defaults off. The default memory is `NoMemory`. Semantic cache, rate limits, document chunks, and `demo/` are not in this tree. Citation layer (c) and pgvector are stretch.

| Tag | Increment | Owners | Scope |
| --- | --- | --- | --- |
| v0.0.0 (tagged) | Skeleton and guardrails | Mihir | README, folders, env examples, gitignores, contracts, CI that blocks a tracked `.env` and an NVIDIA key string |
| v0.1.0 (tagged) | First Zetaris source and seed views | Built: Urvashi, Saleeta. Owner now: Mihir (takeover 2026-10-25) | Open-Meteo Flood (GloFAS), seed views, sync + verify. Also in this tag: core sources, provenance, `ingestion/feeds/`, and migration `033` `pegel_levels` |
| v0.2.0 (tagged) | Live demo stack | Ayush, Zain | Agents graph, HITL, Judge, insurer desk, engines sidecar (present, not called), fast lane, parallel Zetaris. Early landings of v0.4, v0.5, v0.6, v0.7, v0.8, and v0.10, as listed above |
| v0.3.0 (tagged) | Live gauges and hazard_now | Built: Urvashi, Saleeta. Owner now: Mihir (takeover 2026-10-25) | [#24](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/24) `hazard_now` (`034`, `035`), [#28](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/28) gauge views, [#29](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/29) `042`/`043`. [#26](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/26) tag policy and [#27](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/27) judge lane ids are in the same tag. Laptop Zetaris e2e deferred to the morning of 26 Oct 2026. Not this tag: core sources, provenance, `ingestion/feeds/`, and `033` `pegel_levels` (those shipped in v0.1.0). Next tag: `v0.9.0` when #15 and #16 are load-bearing, otherwise `v1.0.0-rc.1` |
| v0.4.0 (inside v0.2.0) | Investigator + Skeptic | Zain, Ayush | Watchers → Investigator → Skeptic, at most 3 rounds. World Model board waits on #15 |
| v0.5.0 (inside v0.2.0) | Live views, API, compose | Zain, Ayush, Mihir | `FF_LIVE_DATA`, FastAPI runs and SSE, compose. Urvashi remains Zetaris expertise |
| v0.6.0 (inside v0.2.0) | Exposure and playbook | Ayush, Zain | Deterministic exposure SQL, playbook actions that cite claims |
| v0.7.0 (inside v0.2.0) | UI v1 | Zain (UI path). Content: Saleeta | Map, chain, evidence drawer with layers (a) and (b), licence badges. Mihir landed the console |
| v0.8.0 (inside v0.2.0) | Human-in-the-loop | Zain (tests: Mihir) | `interrupt()`, SQLite checkpointer, approval API, audit log |
| v0.9.0 (not shipped) | Memory | Ayush (tests: Zain) | Not load-bearing until #15 and #16. H-MEM recall and write-on-approval, trust ledger, thread memory. Sidecar is `engines/` |
| v0.10.0 (inside v0.2.0) | Judge before HITL | Zain, Mihir | Per-claim grounding and citation scores in the approval payload |
| v0.11.0 (stretch) | Layer (c) | Urvashi, Saleeta, Mihir | Stretch. Hierarchical chunks in pgvector (`FF_RAG_DOCS` stays off). Valencia 2024 and Ahr 2021 eval items are already in `evals/` inside v0.2.0 |
| v0.12.0 (not shipped) | Cache, limits, replay | Ayush, Mihir, Zain | Semantic cache, rate limits, past runs, labelled replay. Not in this tree |
| v1.0.0-rc.1 | Demo freeze | All (tag: Mihir) | Mon 20:00. Only `fix/*` after this. Candidates are `rc.N`, not `v0` patch tags |
| v1.0.0 | Release | Mihir | Security review, public repo, GitHub Release, submission |

### Feature flags

Flags live in env and, later, `config/flags.yaml`. Skeleton defaults are in `agents/.env.example` and are off wherever the behaviour does not exist yet.

| Flag | v1.0 default | Purpose |
| --- | --- | --- |
| `FF_LIVE_DATA` | on | Read `floodsense.*` instead of `floodsense_seed.*` |
| `FF_SKEPTIC` | on | Skeptic loop |
| `FF_JUDGE` | on | Score claims before the approval interrupt |
| `FF_HITL` | on | Approval interrupt before any outbound action |
| `FF_HMEM` | off until #15 and #16 merge | Long-term memory. Not load-bearing on main. Default in code is off (`NoMemory`) |
| `FF_RAG_DOCS` | off | Stretch. Layer (c) document citations in pgvector. Not a v1 gate |
| `FF_SEMANTIC_CACHE` | off (not in tree) | Similar query served from a previous good answer, labelled |
| `FF_CACHED_REPLAY` | off, on if a live service fails | Labelled replay of a recorded run |
| `FF_EFAS`, `FF_EXTRA_SEGMENTS` | off | Stretch |

## Repository layout

What is on `main`:

```text
README.md
CHANGELOG.md
compose.yaml          # API, agents, engines, UI. pgvector and Redis are profiles
tasks.py              # up, down, zetaris-sync, engines-test, test, lint. No Make.
.env.example
ingestion/            # Mihir, including live gauges (PEGELONLINE). Saleeta secondary on prep and the demo
zetaris/migrations/   # Mihir — numbered SQL, applied by zetaris-sync
agents/               # Ayush, Zain — LangGraph graph, HITL, Judge. No engines client yet
api/                  # Zain, Ayush — FastAPI proxies runs, SSE, and approval
ui/                   # Citizen page and insurer console. Zain owns the path
engines/              # Ayush — H-MEM and World Model sidecar
evals/                # Saleeta, Zain, Mihir — Valencia 2024 and Ahr 2021. Not tagged
infra/                # Mihir
docs/                 # Mihir — this file, ownership, C4, ADRs
contracts/            # Mihir — JSON Schema shared by agents, API, and UI
.github/workflows/    # Mihir — lint, test, secret scan, migration dry run, engines
scripts/zetaris_sync.py      # applies migrations, then verify
scripts/nightshift_check.py  # Ayush — local Nightshift check
pgvector/.env.example        # optional RAG profile; layer (c) is stretch
```

The gameplan v2 draft placed migrations at `ingestion/zetaris/`. This tree keeps prep in `ingestion/` and SQL in `zetaris/migrations/` so the sync command has one obvious directory. `knowledge/` and `demo/` are not folders yet.

## Zetaris sync

Each of us runs Zetaris locally. Objects stay in sync because they are code.

`python tasks.py zetaris-sync` runs `scripts/zetaris_sync.py` with the same interpreter, applies pending migrations in order through each person's own `ingestion/.env` (host URL `127.0.0.1`, not `agents/.env`), records SHA-256 and time in `.zetaris-sync/ledger.json`, and runs verify queries. CI runs `python scripts/zetaris_sync.py sync --dry-run` and does not apply SQL. Nobody edits views by hand in the SQL Editor. Exploring is fine. Anything that should last becomes a migration and a pull request.

`reset` is not implemented. It prints that and sends no SQL.

Verify output should match on every machine. That is the definition of "in sync". Credentials stay per person. No agent creates or fetches Zetaris keys.

## Running our app

`python tasks.py up` runs `docker compose -p floodsense-app up -d --build` in this repo (Windows: `py tasks.py up`). The `-p` is required: an exported `COMPOSE_PROJECT_NAME` overrides the `name:` field and would attach this stack to another project. The task script also pins `--project-directory` and `-f compose.yaml`, so `COMPOSE_FILE` cannot select another compose file. It starts the API, the agent runtime, the engines sidecar, and the UI. pgvector and Redis start with `python tasks.py up-all` (`--profile rag` and `--profile cache`). No Make, and no `&&`, so PowerShell 5.x can run it.

The stack reaches Zetaris and Nightshift through the host, as a normal client. Inside a container, `127.0.0.1` is the container itself, so URLs use `host.docker.internal`. With Docker Engine on WSL, `host-gateway` may not reach a service bound only to `127.0.0.1`. Ayush (Nightshift) and Urvashi (Zetaris) check that on Thursday. Fallback: run the API and agents on the host, and keep UI, pgvector, and Redis in compose. The `.env` URLs make that a configuration change.

Published ports bind to `127.0.0.1`: `18000` (API), `15173` (UI), `8300` (engines sidecar), `15432` (pgvector), `16379` (Redis). Agents publish nothing. The engines sidecar is in this compose file. Agents in compose use `ENGINES_URL=http://engines:8300`. On the host that URL is `http://127.0.0.1:8300`. Redis has no password. The pgvector example password is a local placeholder. Loopback is what keeps those off the LAN.

`python tasks.py down` stops our project only. It does not remove named volumes. It does not stop Zetaris. It still runs when `pgvector/.env` was never created.

## Citations

Every claim shows its sources. A claim is any sentence that states a fact, a number, or a cause. One citation record feeds the agents, the Judge, the UI, and memory. Owners: Urvashi, Saleeta, and Mihir, used by every agent and screen.

| Layer | What the user sees | When |
| --- | --- | --- |
| (a) Zetaris evidence | `queryId`, SQL, view, sample rows | In `v0.2.0` (agents and the UI) |
| (b) Original source | URL, publisher, licence, attribution, access date, from `floodsense.provenance` | Provenance shipped in `v0.1.0`. The UI shows it from `v0.2.0` |
| (c) Document passage | For example "EMS report, p.12, para 3", plus a 1–2 sentence quote | Stretch. pgvector, behind `FF_RAG_DOCS`. Not a committed increment |

Citation record (v1 contract, column names are a proposal until Urvashi and Saleeta check the real fields):

`citation_id`, `claim_id`, `layer` (`a` \| `b` \| `c`), `source_url`, `title`, `publisher`, `accessed_at`, `licence`, `attribution`, `locator` (section, page, paragraph, lines), `quote` (1–2 sentences), `content_sha256`, `storage` (`full_text` \| `pointer`), optional `query_id`.

Evidence (layer a): `query_id`, `view`, `sql`, `rows_sample` (at most 20), `row_count`, `executed_at_utc`.

What we store depends on the licence:

| Source | What we store | How we cite |
| --- | --- | --- |
| Open-licensed (Copernicus EMS / EFAS / GloFAS, Datenlizenz Deutschland, AEMET OpenData, CC BY papers) | Full text or data. Chunks and embeddings in pgvector only if the stretch path is built | Layers (a) and (b), with the attribution the licence asks for. Layer (c) is stretch |
| Paywalled or copyrighted (news, closed journals) | Pointer only: URL, title, publisher, date, locator, plus a short quote. No full text | Link, 1–2 sentence quote, access date |

Documents are split on their own structure (doc → section → page → paragraph → lines), not into blind fixed-size windows. A retrieved chunk keeps that path next to its embedding. The quote is checked against the stored hash before the claim is accepted.

Vector search is open, and it is stretch. Desk research on 22 Oct 2026 found no documented vector index in Lightning SQL for our edition. Working assumption, recorded in ADR 0009 and not a v1 gate: pgvector in the `rag` profile would store chunks and embeddings; agents would query it directly; the same Postgres may be registered in Zetaris as a JDBC source so metadata still has a `queryId`. `FF_RAG_DOCS` stays off. Nightshift runtime 1.4 documents no `/v1/embeddings`. Ayush confirms with `GET /v1/models`.

## Data we start with

Working decision for this build:

1. Start with German state gauges.
   - Bavaria: Hochwassernachrichtendienst / Bayerisches Landesamt für Umwelt (`hnd.bayern.de`). The site showed offline during the 22 Oct 2026 check. LfU download services we saw are CC BY 4.0. Confirm the HND terms before ingesting.
   - North Rhine-Westphalia: LANUK hydrological data via Open.NRW. Checked gauge datasets were under Datenlizenz Deutschland – Zero – 2.0. Confirm per dataset.
   - Rhineland-Palatinate: Ahr gauges. Their terms are a separate check from NRW.
2. Then go EU-wide for the demo and the product path: Copernicus EMS (EMSR773 Valencia, July 2021 rapid mapping, EFAS as stretch), GloFAS discharge, AEMET and SAIH Júcar for Valencia, OpenStreetMap sites, plus a synthetic insurer portfolio that is clearly labelled synthetic.
3. Open-Meteo (Flood / GloFAS REST and the rain archive) is fine for the hackathon. The data is CC BY 4.0 and the public API is free for non-commercial use. Replace Open-Meteo before any paid product. It is not a dependency we ship in a commercial offering.

Migration `033` `pegel_levels` and `ingestion/feeds/` shipped in `v0.1.0` (PEGELONLINE, WSV; Rhine at Bonn, Köln, and Koblenz). Mihir owns that path (takeover 2026-10-25). `v0.3.0` adds [#28](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/28) gauge views, [#24](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/24) `hazard_now`, and [#29](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/29) migrations `042` and `043`. Laptop Zetaris e2e for that tag is deferred to the morning of 26 Oct 2026. The state portals in the list above stay a terms check. DWD via Bright Sky stays Hold (`docs/legal/sources.md`).

Attribution strings we show, aligned with `ingestion/prep/provenance.csv` and `docs/legal/sources.md`:

- Copernicus EMSR773: `Copernicus Emergency Management Service (© 2024 European Union), EMSR773`. That is the CEMS Citation Guidelines line (activation year 2024). The older `Generated using Copernicus Emergency Management Service information [year]` wording is not the string we store.
- PEGELONLINE (live gauges, Mihir): `Quelle: WSV, PEGELONLINE`. Courtesy only. DL-DE->Zero-2.0 names no required wording.
- AEMET: `© AEMET` or `Información elaborada por la Agencia Estatal de Meteorología`
- Open-Meteo: `Weather data by Open-Meteo.com`
- OpenStreetMap: `© OpenStreetMap contributors`
- Synthetic portfolio: `Synthetic portfolio, generated for the demo. Not real policies`
- Bavaria, pending confirmation, not ingested: `Datenquelle: Bayerisches Landesamt für Umwelt, www.lfu.bayern.de`
- Cross-state portal (warnings and classes only, not ingested): `Datenquelle: www.hochwasserzentralen.de, Stand: TT.MM.JJJJ hh:mm`

## Data-use rules

Working rule, not legal advice. These are the defaults while we build. A commercial launch needs a real legal review.

| Rule | What we do |
| --- | --- |
| Attribution is not permission | We need a licence or a legal exception first, then we attribute as that licence asks |
| Open data | Datenlizenz Deutschland, CC BY 4.0, and the Copernicus terms may be used, combined, and shown, with the required attribution |
| Short quotes | A short quote that supports a point we make, with the source named (Germany: quotation right, §51 UrhG). We do not copy full articles |
| Text and data mining | We respect `robots.txt` and machine-readable TDM opt-outs (DSM Directive Art. 4, §44b UrhG) and delete mined copies when we no longer need them |
| Social platforms | We follow each platform's terms |
| Show it | The UI shows licence and attribution next to the citation. The README lists sources and licences |

Day-1 task (Saleeta and Urvashi): open the terms page of every source we ingest or cite, at least `hnd.bayern.de`, LANUK NRW, the Ahr gauges, Copernicus EMS / EFAS, AEMET, SAIH Júcar, Open-Meteo, and OSM. Record licence, attribution text, and any TDM opt-out. Sources we cannot clear stay pointer-only.

## LLM-as-a-Judge

After the Playbook node and before the human, the Judge scores each claim. It does not approve anything. The human sees the scores and remains the final judge. Owners: Zain and Mihir. That work shipped inside `v0.2.0` (the old `v0.10.0` row).

| Check | Question | How |
| --- | --- | --- |
| Coverage | Does every claim have at least one citation? | Deterministic |
| Citation faithfulness | Does the quote come from the source, and does the locator resolve? | Hash and locator, then the model checks meaning |
| Grounding | Does the evidence support the claim (`supported`, `partial`, `unsupported`)? | Deep Nemotron lane via Nightshift, seeing only the claim and its evidence |
| Numbers | Does every number match its Zetaris result? | Deterministic, with a tolerance |
| Licence | Is full text shown from a pointer-only source? | Deterministic, from the citation record |

Output per claim: `claim_id`, `grounding`, `citation_faithful`, `numbers_match`, `score` (0–1), `rationale`, `model_id`, plus an overall score. Both go into the approval payload and the UI.

An unsupported claim may get one repair round back to Playbook. Otherwise it is flagged. The Judge never silently deletes or rewrites a claim. On the eval set we compare Judge labels with human labels and report agreement. The threshold is a proposal until the first eval run.

Two routing modes, no `meterless/auto` in the demo. Nightshift model ids are routing modes, so the app asks for a disposition and the lanes configured in Nightshift pick the model:

- Fast: `meterless/fast`
- Deep: `meterless/deep`

Today Nemotron 3.5 Super VL 120B A12B (`nvidia/nemotron-3.5-super-vl-120b-a12b`) answers both. Nightshift picks the faster lane, and Super VL beats Nemotron 3.5 Lightning 30B A3B on speed (about 0.5 s against 2.6 s) as well as quality; Lightning stays configured as a second lane. NVIDIA deprecated the `nvidia/nemotron-3-super-120b-a12b` endpoint. `python scripts/nightshift_check.py` shows which model answered each tier, and `--probe` shows what every routing id reaches.

Every call goes through one Nightshift client (`METERLESS_BASE_URL`, timeout 180 s) with `Authorization: Bearer`, `meterless-app`, and `meterless-scope: user`. The model id that answered is logged on the trace.

## Evaluation set

Two real floods. The headline number is the hallucination rate: the share of claims that their own citations do not support. Saleeta and Urvashi build the set. Zain and Mihir run the metrics before the release candidate.

| Event | Official data | News |
| --- | --- | --- |
| July 2021, NRW and the Ahr valley | LANUK NRW gauges via Open.NRW; Ahr gauges run by Rhineland-Palatinate (terms to check); DWD rain; Copernicus EMS rapid mapping | Public reporting, quoted briefly with links |
| October 2024, Valencia | AEMET, SAIH Júcar (access to verify), Copernicus EMSR773, GloFAS via Open-Meteo for the hackathon | Public reporting on the alert timeline, quoted briefly with links |

Each item has a question, the facts a good answer must contain, the allowed sources, a reference answer with citations, and human labels per claim. We propose at least 10 items per event. The exact count is Saleeta and Urvashi's.

Proposed targets, for the team to confirm:

| Metric | Definition | Proposal |
| --- | --- | --- |
| Citation coverage | Claims with at least one citation / all claims | 100% |
| Citation support | Citations that support their claim / all citations | ≥ 90% |
| Quote fidelity | Quotes whose hash and locator match / all quotes | 100% |
| Numeric accuracy | Numbers equal to their Zetaris result / all numbers | 100% |
| Hallucination rate | Claims not supported by their citations / all claims | ≤ 5%, reported per release |
| Judge–human agreement | Claims where the labels agree / all labelled claims | Reported; sets the Judge threshold |

## Caching and the honest demo

Live calls are slow and can fail during the demo. The API grows three behaviours, pitched as scale and cost engineering: many analysts ask about the same event.

| Feature | Behaviour | Owner |
| --- | --- | --- |
| Semantic cache | A previous successful answer for the same or a very similar query (event, customer, replay time, flags). Only answers that finished and passed the Judge are cached. TTL is shorter for live data than for historical replays. | Ayush |
| Clear labelling | Every response carries `served_from` of `live`, `cache`, or `replay`, and `cached_at` when it is not live. The UI shows a banner such as `cached at HH:MM` (for example "Cached answer from 14:32 · not live · original run R-123"). | Ayush (API), Zain (UI) |
| Rate limiting | Per-client HTTP 429 with `Retry-After`, plus a global cap on concurrent Nightshift calls. | Mihir |
| Past runs | `GET /runs/past` lists earlier runs. Replaying one is labelled replay. | Ayush |

Live first: the demo runs live when the pinned lanes answer `GET /v1/models`. If Nightshift or Zetaris fails, the console switches to the recorded run and shows the replay banner. Saleeta's script has both paths, and she says which one is playing.

Cached or replayed output is always labelled `cached at HH:MM`. It is never presented as live. Not in the UI, not in the video, not in the deck. The trace keeps the original run's timestamps.

## Branching and tags

`main` is the integration branch. Short-lived branches (`feat/<area>-<topic>`, `fix/…`, `chore/…`) merge through a pull request with green checks and one review from outside the pair. Product tags on the 0.x line are `v0.MINOR.0` only. Tagged today: `v0.0.0`, `v0.1.0`, `v0.2.0`, and `v0.3.0` (live gauges and `hazard_now`). Laptop Zetaris e2e for `v0.3.0` is deferred to the morning of 26 Oct 2026. The next tag is `v0.9.0` once #15 and #16 are load-bearing, or `v1.0.0-rc.1` at the Monday freeze. There is no `v0.x.y` fix tag. Pairs share a branch, rebase before push, and delete the branch after merge.

Merge at least daily, at the 19:30 window. Mihir tags a green `main`. Tags are never moved or deleted. A fix on the 0.x line does not get its own tag. It is part of the next `v0.MINOR.0`. From `v1.0.0-rc.1` (Mon 20:00 CET) only `fix/*` pull requests land. Those candidates are `rc.2`, `rc.3`, and so on.

The repo stays private during the build and switches to public before submission, after the security review. On GitHub Free, rulesets and enforced code owners apply once the repo is public. Until then the team rules above are the protection, together with the CI workflow in `.github/workflows/ci.yml`.

## Secrets

- Filled env files stay untracked. Commit `.env.example` only.
- Each person creates their own Zetaris API key and their own Nightshift runtime token.
- The NVIDIA provider key lives only in Nightshift's Providers tab. It is not an application env var, a GitHub secret, a test fixture, or a Cursor model setting.
- SQL, logs, screenshots, and prompts do not contain tokens. Placeholders in examples are empty or obvious stand-ins.
- If a secret is committed, rotate it. Deleting the file is not enough.
- CI (`.github/workflows/ci.yml`) rejects a tracked `.env` other than `.env.example`, and fails on an NVIDIA `nvapi-` key or another secret gitleaks flags in that pull request's commits (on a push to `main`, in the pushed commits). `.gitleaksignore` may name a single finding by fingerprint. It is not a path or rule allowlist. See [adr/0008-ci-runner-github-hosted.md](adr/0008-ci-runner-github-hosted.md).

## Open points and proposals

Owners in parentheses. A line that names a result is settled. The rest is still open.

- Zetaris vector features in our edition, pgvector registration from the Zetaris containers, vector column mapping, and pushdown (Urvashi, Thu).
- Whether Nightshift serves embeddings, and which model we use if it does not (Ayush with Urvashi).
- Container access to host services under WSL for Zetaris `:8888` and Nightshift `:8088` (Ayush, Urvashi).
- Terms of every source, especially `hnd.bayern.de` (offline during the check), the Ahr gauges, SAIH Júcar, and Open-Meteo for commercial use (Saleeta, Urvashi). Open-Meteo is accepted for the hackathon and is to be replaced before a paid product.
- Lightning SQL on Zetaris 2.4.3.1: `IF NOT EXISTS` is not supported. `OR REPLACE` works for `SCHEMASTORE VIEW`. Recorded in `zetaris/README.md`.
- The engines sidecar is `engines/` (TypeScript, Ayush). The agents package does not call `ENGINES_URL` yet.
- Cursor plan features and cost for Bugbot and cloud agents (Mihir).
- Whether the repository owner has GitHub Pro. Not assumed. Rulesets while private are not part of the plan.
- View column names in the contracts section are a proposal until checked against the real source fields (Urvashi, Saleeta).
- Eval targets and the Judge threshold are proposals until the first eval run (Zain, Mihir).
- The data-use section is a working rule, not legal advice.
- Seed rows are FILESTORE CSVs. `ingestion/prep/stage_local_zetaris.py` stages them before migration 010.

## Definition of done (every later pull request)

- An acceptance test exists and the checks are green.
- The change stays in owned folders, or the owners reviewed it. Contract changes were announced.
- One review from outside the pair.
- No secrets in code, tests, fixtures, logs, or screenshots.
- New Zetaris objects arrive as a new migration plus a verify query.
- Every new claim carries a citation record. Every LLM call goes through the Nightshift client.
- Unfinished behaviour sits behind a flag. Cached output is labelled.
- README or docs updated when setup changed.

## Still open

- `v0.3.0` is tagged (live gauges, `hazard_now`, migrations `042` and `043`, the tag policy, and judge lane ids). Laptop Zetaris e2e is deferred to the morning of 26 Oct 2026. The next tag is `v0.9.0` when #15 and #16 are load-bearing, otherwise `v1.0.0-rc.1`. The 0.x line stays `v0.MINOR.0` only.
- The HITL interrupt from #4 is in `v0.2.0`.
- H-MEM and the World Model are not load-bearing until Ayush #15 and #16 merge. The agents package does not call `engines/`. `FF_HMEM` defaults off. The default memory is `NoMemory`.
- Citation layer (c) and pgvector are stretch. `FF_RAG_DOCS` stays off.
- Semantic cache and rate limits are not in this tree.
- `knowledge/` and `demo/` are not folders yet.
- `zetaris-sync` has no `reset`.
- No pre-commit hook. `python tasks.py lint` is the local check. No enforced CODEOWNERS file.
- ADR 0001 is Accepted. ADRs 0002–0009 are Proposed.
