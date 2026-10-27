# FloodSense EU: submission

FloodSense EU explains why a place in Europe is at flood risk. Every claim cites the data row or document passage it came from. A Skeptic challenges the reasoning, a Judge scores it, and a human approves any outbound action.

Open Agent Hackathon 2026, Track 02. Technical detail is in [architecture/technical-highlights.md](architecture/technical-highlights.md).

## Sponsor usage

### Zetaris: the only data path for agents

What it does. Agents read hazard, exposure, gauge, provenance and document metadata only through Zetaris SQL ([ADR 0003](adr/0003-zetaris-only-data-path.md)). Zetaris federates CSV files (FILESTORE tables), REST tables that call Open-Meteo, and a PostgreSQL (pgvector) database registered over JDBC.

Where in the code:

- Client: `agents/floodsense_agents/zetaris.py`. Views the agents may read: `contracts/views.yaml`.
- Migrations: `zetaris/migrations/*.sql` (numbered, `001` to `041`). Examples: `010_seed_sources.sql` (FILESTORE CSV tables), `003_create_rest_table_glofas_discharge.sql` (REST table), `034_create_view_hazard_now.sql` (live view), `015_create_view_provenance.sql`.
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
- World Model board: `GET http://127.0.0.1:8300/wm/board?run_id=<id>`.

### NVIDIA: Nemotron models and NIM embeddings

What it does.

- The Nightshift lanes are answered by NVIDIA Nemotron (today `nvidia/nemotron-3.5-super-vl-120b-a12b` for both lanes, per `docs/architecture/c4.md`).
- Document embeddings for citation layer (c) come from NVIDIA NIM `POST /v1/embeddings` with `nvidia/nemotron-3.5-embed-1b` (2048 dimensions). Nightshift does not serve embeddings, so this is the one model call that does not go through Nightshift ([ADR 0009](adr/0009-vector-search-next-to-zetaris.md)).

Where in the code: `agents/floodsense_agents/nim_embed.py` (query embeddings, `input_type: query`), `scripts/rag_ingest.py` (passage embeddings, `input_type: passage`), `pgvector/migrations/001_rag_chunks.sql` and `002_rag_embed_model_nemotron35.sql`.

How a judge can see it. `model_id` on each trace event names the Nemotron model. A layer (c) citation shows a document passage with its licence, a `content_sha256` of the quote, and a Zetaris `query_id`.

The NVIDIA chat key lives only in Nightshift's Providers tab. `NVIDIA_NIM_API_KEY` is a separate, gitignored key for embeddings.

### Cursor: how we built it

What it does. The team used Cursor to write and review code. The repository holds a Cursor skill that sets the merge bar for cloud-agent pull requests.

Where in the code: `.cursor/skills/floodsense-pr-review/SKILL.md` (see [CHANGELOG.md](../CHANGELOG.md), PR #35).

How a judge can see it. Read the skill file. TODO: add which Cursor features each person used (Bugbot, cloud agents, Composer) and links to example PRs.

## Problem and users

In a flood, three groups need the same facts in different forms.

- Citizens: "Is my street at risk tonight, and what do I do?"
- Civil protection: "Which areas need attention first, and why?"
- Insurers (the payer): "Which insured sites are exposed, and what should we tell the customer?"

Founder insight. Our architect worked at an NRW government agency. In Germany, river gauges are run state by state, so data sits in many places. Hotline staff who take calls in a flood are not flood experts. They need a short, cited answer they can trust and repeat.

## What is built

- A LangGraph agent: Scope, Watchers, Investigator, Skeptic (revise loop), Exposure, Playbook, Judge (repair loop), human approval, Learn.
- Three citation layers: (a) Zetaris data rows, (b) source provenance, (c) document passages with hash-checked quotes.
- Live mode: a `hazard_now` view with past and forecast rows, a mode classifier for "now" vs past-event questions, and a staleness flag.
- A web UI with two desks. Citizen: Now, Overview, My area, What to do, Evidence. Insurer: Now, Approvals, Portfolio, Sites / map, Alerts, Review.
- An API with a semantic cache, labelled replay, and rate limits.
- Seeded demo events: Valencia 2024 and Ahr 2021 (`evals/valencia_2024.yaml`, `evals/ahr_2021.yaml`).

## Honest limits

- The insurer portfolio is synthetic. It is labelled as synthetic in the data (`zetaris/migrations/018_label_exposure_synthetic.sql`) and in the UI.
- Discharge comes from Open-Meteo (GloFAS-based model output). It is modelled data, not an official warning.
- EFAS real-time data is for partner organisations only. We do not use it.
- The Ahr gauges are not on PEGELONLINE. Our live gauges are the Rhine at Bonn, Köln and Koblenz.
- A live run takes about 15 minutes on Nightshift today. A test-only provider switch (`LLM_PROVIDER_SWITCH`, `agents/floodsense_agents/nightshift.py`) runs the same graph in about 50 seconds on a faster provider. The demo and the submission do not use that switch.
- The demo uses recorded runs, shown as labelled replays. A replay or cache answer is never shown as live.

## Evaluation

TODO: fill in numbers from `evals/run_evals.py` (grounding rate, citation faithfulness, Judge score, Skeptic catches) for Valencia 2024 and Ahr 2021.

| Metric | Valencia 2024 | Ahr 2021 |
| --- | --- | --- |
| Grounded claims | TODO | TODO |
| Citation faithful | TODO | TODO |
| Mean Judge score | TODO | TODO |

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

Live gauges and rain (poll every 15 minutes and stage for Zetaris):

```powershell
python ingestion/feeds/feeds.py pull --stage --interval 900
```

Document corpus for layer (c):

```powershell
py tasks.py fetch-rag-corpus
python scripts/rag_ingest.py   # needs the rag profile and NVIDIA_NIM_API_KEY
```

TODO: confirm the exact `rag_ingest.py` arguments before the demo.

## 30-second judge tour

1. Open `http://127.0.0.1:15173/`. Pick the citizen desk, page Now. Ask a question about Valencia.
2. Look at the answer: each claim has citations. Each data citation shows a Zetaris `query_id`. The banner says replay or cache when the answer is not live.
3. Switch to the insurer desk, page Approvals. Approve or edit the proposed action. Nothing goes out without this step.
4. Open `http://127.0.0.1:18000/runs/<run_id>` to see the trace with `node`, `lane` and `model_id` per step.
5. Open `http://127.0.0.1:8300/wm/board?run_id=<run_id>` to see the World Model hypothesis board.

TODO: add the hosted demo URL and a recorded run id, if we publish one.
