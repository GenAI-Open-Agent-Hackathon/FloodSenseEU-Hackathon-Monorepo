# Handover: FloodSense EU (Open Agent Hackathon 2026, Track 02)

Written 27 Oct 2026 and updated for the final state of `main` (`c9ff924`). **Submission is due 27 Oct 21:00 CET.** Read this first, then `README.md`,
`agents/README.md`, `ui/README.md` and `CHANGELOG.md` (`[Unreleased]`).

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
  `py tasks.py zetaris-sync`). 45 sources = 26 PEGELONLINE gauges + 11 GloFAS points + 8 Valencia demo points.
- **LLM**: only through the **Nightshift** gateway (`:8088`, `meterless/fast` and `meterless/deep`), Nemotron models.
  NVIDIA rate-limits (429): `agents/floodsense_agents/nightshift.py` has backoff, a concurrency cap (3) and a pacer (35 rpm).
- **Memory**: H-MEM and World Model in `engines/` (`:8300`). Written only on approval. Demo seeds are labelled `demo-seed`.
- **RAG**: pgvector + NVIDIA NIM `nemotron-3.5-embed-1b`. 25 documents / 1,859 passages (`corpus/`, `scripts/rag_ingest.py`).
- **API** (`api/`, `:18000`): Redis cache, rate limits (10/min, 2 concurrent), SSE events, `GET /system`, `/watch/*` (Control tower),
  `GET /views/{name}` with a TTL and stale-if-error cache (`api/app/views_cache.py`).
- **Control tower** (`agents/floodsense_agents/tower.py`): rule-based watch loop, no model calls (`FF_WATCH_LOOP`, `WATCH_INTERVAL_S` 900);
  auto-assess is off by default (`FF_AUTO_ASSESS`), capped at 1 per hour and 3 per day, and never approves.
- **UI** (`ui/`, `:15173`): React/Vite. Run `cd ui && npm ci && npm test`.
- **Poller**: `pegel-poller` compose service refreshes PEGELONLINE every 10 min into Zetaris (mounts `docker.sock`, dev only).

## How to run everything (fresh clone)

1. `py tasks.py up-all` (Windows) or `python3 tasks.py up-all`. Needs Docker Desktop and the separate Zetaris stack.
2. `py tasks.py zetaris-sync` to apply the Zetaris migrations.
3. Document ingest: `python tasks.py fetch-rag-corpus` then `python scripts/rag_ingest.py` (needs `PGVECTOR_DSN`, with the
   host port 15432 when run outside compose, and `NVIDIA_NIM_API_KEY`; use a venv that has `pypdf` and `psycopg`).
4. `py tasks.py demo-seed` (labelled demo memories and warmed cache). Set `FF_SEMANTIC_CACHE=true` in `api/.env` first.
5. Open http://127.0.0.1:15173. Env files (`agents/.env`, `api/.env`, `ingestion/.env`) are gitignored. Never commit keys.

Test suites (CI runs them): `python -m unittest discover -s tests` in `agents/`, `api/`, `contracts/`, `scripts/`;
`ruff check`; UI `npm test`, `npm run lint`, `npm run build`. Use a venv from `agents/requirements*.txt`; the system
Python on the main dev machine has a wrong langgraph.

## State at handover

`main` is `c9ff924` (merge of PR #101) and is feature-frozen. Release documentation is on the branch `docs/release-v1`. Everything below is merged, reviewed by an independent agent, and passed CI.

### Merged to `main` since the first handover (27 Oct)
- #90 global Live | Past flood and Demo data switches, curated Approvals and Review.
- #91 calm answers: the deterministic `plain` object and CalmAnswer.
- #92 tech trace: "How this answer was made" tiles. It is rendered inside the calm answer (`CalmAnswer.tsx`), on Review and on How it works.
- #94 Civil protection operator desk (Situation board, call script, own approvals).
- #95 Control tower (watch loop, activity feed, `/watch/*`), #97 its follow-ups (plain feed failures, optional `detail`).
- #96 views cache with stale-if-error for `GET /views/{name}`.
- #98 final UI polish, #99 status wording (Normal / Watch / Elevated; the contract enum `Warning` was renamed `Elevated`).
- #100 and #101 H-MEM recall fixes (approved live runs recalled by place; the newest memories are read too).
- Earlier the same day: router lanes, front door, Europe live watch, forecast lane and DWD ICON weather, live agent pipeline over SSE, approval cards, insurer documents, 13 past-flood documents with 59 cited demo memories, demo seed and System page, NVIDIA backoff, live-first desks, poller container, clarity pass, How it works page.

There are no open feature branches to merge. The `feat/control-tower` and `feat/operator-desk` branches named in the first handover are merged (#95, #94). Unverified from the repository: the state of the older pull requests #88 and #68 (from teammates); check them on GitHub.

Workflow used all day: branch, coding agent, independent review agent, review findings as PR comments, rework, re-review, CI green, merge, delete branch, update docs and CHANGELOG in every PR. `gh` is at `C:\Program Files\GitHub CLI\gh.exe`; `gh pr view --comments` fails with this token, so use `gh api repos/<owner>/<repo>/issues/<n>/comments`.

### Verified on the live stack
- The approve-and-remember loop: approving run `f6cc4adbc438` took the H-MEM count from 212 to 214 and the next Orléans forecast recalled the new memory (`mem-213`); this was observed on the demo machine on 27 Oct and is not stored as an artifact.
- Last end-to-end run on Nightshift: every claim cited and judged, 100% coverage on every scenario of the 27 Oct end-to-end run (the stored Nightshift eval evidence is the 4-item subset of that day). Quick lane about 1 s, forecast lane 1 to 4 s (no model writes the answer), full lane 5 to 6 minutes on Nemotron.
- 18 routes across the three desks (the main pages of each) were checked at 375 px with no horizontal scroll; the full navigation has 20 pages.

### Known bugs and weak spots
- Insurer Approvals queue had 29 old test runs (curated in #90). Insurer "Now" page is dense.
- Review's Skeptic/Judge tabs are still the bundled Valencia fixture.
- Overview shows Paiporta "Below the 100 m3/s line" on 29 Oct because the daily value crosses on 30 Oct.
- Sites map uses an 80 m3/s band while Replay uses 100.
- First load of live pages takes 5-10 s (Zetaris views are queried one by one).
- Poller container tested only on Docker Desktop for Windows; `docker.sock` mount is dev-only. `POLL_INTERVAL_S=0` busy-loops.
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

- Decide the licence and add a `LICENSE` file (the README has a marked TEAM block; until then the code is unlicensed).
- Confirm the Cursor wording in `README.md` ("How we built it") and `docs/SUBMISSION.md` (both carry a `TEAM: confirm Cursor wording` marker). Add which features each person used and example PRs.
- Merge `docs/release-v1`, then tag `v1.0.0` and create the GitHub Release (the notes are `docs/RELEASE-NOTES-v1.0.0.md`). No `v1.0.0-rc.N` tag exists.
- Make the repository public, record the demo video, submit. Submission is due 27 Oct 21:00 CET.
- Deck (`E:\Projects\GenAI-Hackathon-2026\Submission\FloodSense-EU-Pitch-v6.pptx`, outside the repo, with the scripts in the same folder): add the new screens (Control tower, operator desk, calm answers, tech trace), verify the death tolls on slides 2 and 4 against `docs/DECK-FACTS.md` (the stored sources disagree in places), fix the repo link and prices on the last slide, refresh slide 8 screenshots, update stale speaker notes.
- Before recording: `LLM_PROVIDER_SWITCH=false` in `agents/.env` (and the root `.env`) and recreate the agents container. For the live demo also set `FF_LIVE_DATA`, `FF_HMEM` and `FF_RAG_DOCS` to true there (the examples ship them off).
- Run `py tasks.py demo-seed` after a rebuild (set `FF_SEMANTIC_CACHE=true` in `api/.env` first), and walk every page in Live, Past and Demo modes once in a browser.
- No ffmpeg on the main dev machine; the Higgsfield account has 0 credits. A self-playing HTML walkthrough is the planned stand-in; the final video should be a real screen recording.

Rebuild command, if the stack must be recreated: `docker compose -p floodsense-app --project-directory . -f compose.yaml --profile rag --profile cache up -d --build agents api ui` (add `-f local/compose.console.yaml` only on the main dev machine, where that untracked file exists).
