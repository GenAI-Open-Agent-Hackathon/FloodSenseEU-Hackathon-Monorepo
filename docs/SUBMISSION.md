# FloodSense EU: submission

FloodSense EU explains why a place in Europe is at flood risk. Every claim cites the data row or document passage it came from. A Skeptic challenges the reasoning, a Judge scores it, and a human approves any outbound action.

Open Agent Hackathon 2026, Track 02. Technical detail is in [architecture/technical-highlights.md](architecture/technical-highlights.md).

## Sponsor usage

### Zetaris: the only data path for agents

What it does. Agents read hazard, exposure, gauge, provenance and document metadata only through Zetaris SQL ([ADR 0003](adr/0003-zetaris-only-data-path.md)). Zetaris federates CSV files (FILESTORE tables), REST tables that call Open-Meteo, and a PostgreSQL (pgvector) database registered over JDBC.

Where in the code:

- Client: `agents/floodsense_agents/zetaris.py`. Views the agents may read: `contracts/views.yaml`.
- Migrations: `zetaris/migrations/*.sql` (numbered, up to `073`). Examples: `010_seed_sources.sql` (FILESTORE CSV tables), `003_create_rest_table_glofas_discharge.sql` (REST table), `034_create_view_hazard_now.sql` (live view), `015_create_view_provenance.sql`.
- Sync and verify: `scripts/zetaris_sync.py` (applies pending migrations, then runs `DESCRIBE` and a row count for each declared view). `py tasks.py zetaris-sync`.
- CI dry run: `.github/workflows/ci.yml`, step "Zetaris migrations (dry run)".
- Document passages: `agents/floodsense_agents/retrieve_docs.py` ranks in Postgres, then reads text and licence through Zetaris ([ADR 0009](adr/0009-vector-search-next-to-zetaris.md)).

How a judge can see it. Every data citation carries the Zetaris `query_id`. In the UI, Ask FloodSense lists each evidence row as `query_id · row count` (`ui/src/components/AskFloodSense.tsx`). In the API, `GET /runs/{id}/citations` returns `query_id` per citation.

### Meterless: Nightshift lanes, H-MEM and World Model

What it does.

- All chat completions go through Meterless Nightshift ([ADR 0004](adr/0004-nightshift-only-llm-calls.md)). The app sends only two lane ids, `meterless/fast` and `meterless/deep`. Nightshift picks the model. The lane-to-model table is at the top of [architecture/c4.md](architecture/c4.md).
- The Meterless engines sidecar (`engines/`, port 8300) runs H-MEM (long-term memory of approved findings) and the World Model (hypothesis board as an append-only event log).

Where in the code:

- Nightshift client: `agents/floodsense_agents/nightshift.py`. Lane choice: `agents/floodsense_agents/settings.py` (`MODEL_FAST`, `MODEL_DEEP`).
- Engines client: `agents/floodsense_agents/engines.py`. H-MEM recall and write-on-approval: `agents/floodsense_agents/nodes/memory.py`, called from `nodes/investigator.py` (behind `FF_HMEM`). World Model writes: `agents/floodsense_agents/nodes/world_model.py` (Watchers, Investigator, Skeptic).
- Engines API: [engines/README.md](../engines/README.md) (`/hmem/recall`, `POST /wm/hypotheses`, `GET /wm/board`).

How a judge can see it.

- `GET /runs/{id}` and the SSE trace `GET /runs/{id}/events`: each trace event has `node`, `lane` and `model_id`.
- The H-MEM recall step appears as a trace event before the Investigator builds its chain (with `FF_HMEM=true` and `ENGINES_URL` set).
- World Model in the UI: the agent pipeline panel (`ui/src/components/AgentPipeline.tsx`) marks the steps that write to it with a "World Model" badge.
- World Model board: `GET http://127.0.0.1:8300/wm/board?run_id=<id>`.

### NVIDIA: Nemotron models and NIM embeddings

What it does.

- The Nightshift lanes are answered by NVIDIA Nemotron. Nightshift picks the model per lane. In the 27 Oct Nightshift eval subset, every row's `model_ids` is `nvidia/nemotron-3.5-lightning-30b-a3b` (see the per-row `model_ids` in [evals/2026-10-27-nightshift-subset.json](evals/2026-10-27-nightshift-subset.json)).
- Document embeddings for citation layer (c) come from NVIDIA NIM `POST /v1/embeddings` with `nvidia/nemotron-3.5-embed-1b` (2048 dimensions). Nightshift does not serve embeddings, so this is the one model call that does not go through Nightshift ([ADR 0009](adr/0009-vector-search-next-to-zetaris.md)).

Where in the code: `agents/floodsense_agents/nim_embed.py` (query embeddings, `input_type: query`), `scripts/rag_ingest.py` (passage embeddings, `input_type: passage`), `pgvector/migrations/001_rag_chunks.sql` and `002_rag_embed_model_nemotron35.sql`.

How a judge can see it. `model_id` on each trace event names the Nemotron model. A layer (c) citation shows a document passage with its licence, a `content_sha256` of the quote, and a Zetaris `query_id`.

The NVIDIA chat key lives only in Nightshift's Providers tab. `NVIDIA_NIM_API_KEY` is a separate, gitignored key for embeddings.

### Cursor: how we built it

What it does. Some team members used Cursor extensively, including Cursor's Grokbot to run subagents. The repository holds a Cursor skill that sets the merge bar for cloud-agent pull requests. The repository's coding, review and documentation work also used Claude Code (Anthropic) with independent review agents: every change went through a branch, an independent review and a pull request (see the pull requests in this repository). The same wording is in the README, "How we built it".

<!-- TEAM: confirm Cursor wording -->
<!-- TEAM-EDITABLE-BLOCK START (Cursor details) -->
Which features each person used, and example pull requests: the team fills this in. Not verified from the repository, which records only the skill below.
<!-- TEAM-EDITABLE-BLOCK END -->

Where in the code: `.cursor/skills/floodsense-pr-review/SKILL.md` (see [CHANGELOG.md](../CHANGELOG.md), PR #35).

How a judge can see it. Read the skill file and the pull request history: each pull request shows its branch, its review comments and the changelog line it added.

## Problem and users

In a flood, three groups need the same facts in different forms.

- Citizens: "Is my street at risk tonight, and what do I do?"
- Civil protection: "Which areas need attention first, and why?"
- Insurers (the payer): "Which insured sites are exposed, and what should we tell the customer?"

Founder insight. Our architect worked at an NRW government agency. In Germany, river gauges are run state by state, so data sits in many places. Hotline staff who take calls in a flood are not flood experts. They need a short, cited answer they can trust and repeat.

## What is built

- A router with four lanes (`reply`, `quick`, `forecast`, `full`). The full lane is a LangGraph agent: Scope, Watchers, Memory, Investigator, Skeptic (revise loop), Exposure, Playbook, Judge (repair loop), human approval, Learn. The other three lanes make no model call.
- A Control tower: a rule-based watch loop over 45 sources with an activity feed, and an opt-in, capped auto-assess that never approves.
- Three citation layers: (a) Zetaris data rows, (b) source provenance, (c) document passages with hash-checked quotes.
- Live mode: a `hazard_now` view with past and forecast rows, a mode classifier for "now" vs past-event questions, and a staleness flag.
- A web UI with three desks and a global Live | Past flood | Demo data switch. Citizen: Now, Replay, Overview, My area, What to do, Evidence, How it works. Insurer: Control tower, Now, Replay, Approvals, Portfolio, Sites / map, Alerts, Review, System, How it works. Civil protection: Situation board, Approvals, How it works.
- An API with a semantic cache, labelled replay, rate limits, a views cache that serves the last good copy when Open-Meteo rate-limits, and `/watch/*` for the Control tower.
- Seeded demo events: Valencia 2024 and Ahr 2021 (`evals/valencia_2024.yaml`, `evals/ahr_2021.yaml`).

## Honest limits

- The insurer portfolio is synthetic. It is labelled as synthetic in the data (`zetaris/migrations/018_label_exposure_synthetic.sql`) and in the UI.
- Discharge comes from Open-Meteo (GloFAS-based model output). It is modelled data, not an official warning.
- The forecast lane's weather forecast is Open-Meteo with the DWD ICON model (CC BY 4.0; DWD is the data originator). The Open-Meteo free API is non-commercial only (under 10,000 calls/day; one forecast question is about 45 calls), so a commercial product needs a paid plan. The status Normal / Watch / Elevated is FloodSense's own screening, not an official warning.
- EFAS real-time data is for partner organisations only. We do not use it.
- The Ahr gauges are not on PEGELONLINE. They belong to the Rhineland-Palatinate state service, so the Ahr is replay only. Live gauges are WSV stations on PEGELONLINE (`ingestion/feeds/pegel_poll.py`).
- Ahr 2021 replay data is reanalysis: ERA5 rain (Open-Meteo Historical Weather API) and GloFAS discharge (Open-Meteo Flood API). Both are far below the published figures for this storm (for example about 1000 m3/s reconstructed at Altenahr). We do not quote literature figures as values of these views (`zetaris/migrations/051_seed_discharge_daily_ahr.sql`, `052_seed_hazard_timeline_ahr.sql`).
- A full live run on Nightshift takes about 6 minutes (mean 385 s and 346 s per run in the 27 Oct subset). Calls stream, and the Investigator calls the model once per link (PRs #63 and #66; see CHANGELOG.md). Investigator links sometimes fall back to the deterministic chain when Meterless' provider deadline (about 45 s) cuts the call. These fallbacks were not counted in the eval runs. A test-only provider switch (`LLM_PROVIDER_SWITCH`, `agents/floodsense_agents/nightshift.py`) runs a full run in about 35 seconds on a faster provider. The demo and the submission default to Nightshift.
- The replay page reads the Ahr 2021 rows from Zetaris (`floodsense_seed` views), not from a UI fixture.
- The demo uses recorded runs, shown as labelled replays. A replay or cache answer is never shown as live.

## Evaluation

All runs on 27 Oct 2026, live Zetaris. `evals/run_evals.py` with `evals/valencia_2024.yaml` and `evals/ahr_2021.yaml`.

### A) Full set, 21 items, test provider Anthropic Sonnet

This uses the test-only provider switch (`--provider anthropic`), not Nightshift. Report: [evals/2026-10-27-anthropic.md](evals/2026-10-27-anthropic.md).

| Metric | Valencia 2024 (10 items) | Ahr 2021 (11 items) |
| --- | --- | --- |
| Hallucination | 5.6 % | 9.1 % |
| Citation coverage | 100 % | 91 % |
| Numeric match | 92 % | 98 % |
| Judge pass | 78 % | 91 % |
| Mean Judge score | 0.92 | 0.87 |
| Forbidden figures | 0 | 0 |
| Mean time per question | 37 s | 29 s |

- Valencia includes one out-of-scope question. It was declined, as expected.
- Almost all of the Ahr loss is one item, ahr-09 (the 15:00 pre-peak replay). On the real ERA5 data it produced 0 claims, and the scorer counts that as 100 % unsupported and 0 % cited. That one item is why Ahr coverage is 91 % (10 of 11) and hallucination 9.1 %. Without it, Ahr hallucination is 0 % and coverage 100 %.
- Known eval-file gap: expected-token hit rates are low (67 % Valencia, 43 % Ahr) because the expected tokens were written against fixture data, not the real data.

### B) Subset on the judged path, Nightshift with NVIDIA Nemotron

Default provider. 4 items: val-02, val-05, ahr-03, ahr-05. Every row's `model_ids` is `nvidia/nemotron-3.5-lightning-30b-a3b`, per the per-row `model_ids` in [evals/2026-10-27-nightshift-subset.json](evals/2026-10-27-nightshift-subset.json). Report: [evals/2026-10-27-nightshift-subset.md](evals/2026-10-27-nightshift-subset.md).

| Metric | Result |
| --- | --- |
| Hallucination | 0 % |
| Citation coverage | 100 % |
| Numeric match | 100 % |
| Judge pass | 100 % |
| Mean Judge score | 0.99 (Valencia), 1.00 (Ahr) |
| Mean time per run | 385 s and 346 s (about 5.8 to 6.4 min) |

Known limit: Investigator links sometimes fall back to the deterministic chain when Meterless' provider deadline (about 45 s) cuts the call. These fallbacks were not counted in the eval runs. Skeptic, Playbook and Judge answer with Nemotron.

## How to run

You need Python 3.10+ and Docker Desktop. Zetaris and Nightshift run as your own local processes. This repository does not start them.

```powershell
py tasks.py init-env       # copy each missing .env.example to .env
py tasks.py up             # API :18000, UI :15173, engines :8300, agents
py tasks.py up-all         # also the rag (pgvector) and cache (Redis) profiles
py tasks.py zetaris-sync   # apply Zetaris migrations, then verify the views
py tasks.py test           # unit tests and UI Vitest
py tasks.py lint
py tasks.py down
```

Compose profiles: `rag` starts pgvector, `cache` starts Redis (`docker compose --profile rag --profile cache up`).

Live PEGELONLINE gauges start with the stack (`py tasks.py up`, service `pegel-poller`, every 10 minutes). Manual run (fetch, write the CSV, copy it into the Zetaris driver; repeat every 15 minutes):

```powershell
py tasks.py pegel-poll --interval 900
```

Other feeds (rain, archive pulls): `python ingestion/feeds/feeds.py pull --stage --interval 900`.

Document corpus for layer (c):

1. `py tasks.py up-all` starts pgvector on `127.0.0.1:15432` (`rag` profile; copy `pgvector/.env` first with `init-env`).
2. Apply `pgvector/migrations/001_rag_chunks.sql`, then `002_rag_embed_model_nemotron35.sql`, with `psql` (see `pgvector/README.md`).
3. `py tasks.py fetch-rag-corpus` checks the corpus sha256 and fetches into `corpus/fetched/`.
4. Set `PGVECTOR_DSN` and `NVIDIA_NIM_API_KEY` in the environment, then run `python scripts/rag_ingest.py`. It takes no arguments and does not print either value.
5. Register the table in Zetaris: `zetaris/migrations/044_register_pgvector_rag_chunks.sql` (applied by `py tasks.py zetaris-sync`).
6. Set `FF_RAG_DOCS=true` for the agents.

## 30-second judge tour

1. Open `http://127.0.0.1:15173/`. Pick the citizen desk, page Now. Ask a question about Valencia.
2. Look at the answer: each claim has citations. Each data citation shows a Zetaris `query_id`. The banner says replay or cache when the answer is not live.
3. Switch to the insurer desk, page Approvals. Approve or edit the proposed action. Nothing goes out without this step.
4. Open `http://127.0.0.1:18000/runs/<run_id>` to see the trace with `node`, `lane` and `model_id` per step.
5. In the agent pipeline panel, the World Model badges show which steps wrote hypotheses. The full board is at `http://127.0.0.1:8300/wm/board?run_id=<run_id>`.

The demo runs locally via docker compose (see README).
