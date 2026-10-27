# Handover: FloodSense EU (Open Agent Hackathon 2026, Track 02)

Written 27 Oct 2026, about 14:45 CET. **Submission is due 27 Oct 21:00 CET.** Read this first, then `README.md`,
`agents/README.md`, `ui/README.md` and `CHANGELOG.md` (`[Unreleased]`).

## What the product is

Explainable flood risk for Europe, with three intended desks: **Citizen**, **Insurer** (the payer), and
**Civil protection / Operator** (the founder's story: hotline staff are not flood experts). Every sentence cites its
source. A person approves anything outbound. Rubric: Impact 30, Technical 20, Innovation 15, Demo 15, Product & UX 10,
Sponsor tech 10 (Zetaris, Meterless Nightshift / H-MEM / World Model, NVIDIA Nemotron, Cursor).

## Architecture in one screen

- **Router** picks a lane per message (`agents/floodsense_agents/router.py`, `front_door.py`):
  - `reply`: greetings, help, thanks, off-topic. Fixed templates, instant.
  - `quick`: live level questions. Reads Zetaris views, deterministic cited claims, deterministic Judge. No model call, ~1 s.
  - `forecast`: "next 48 h / this week" for the 45 watched places. DWD ICON rain (Open-Meteo) + GloFAS + gauges + past
    pattern + H-MEM. No model call, 1-2 s.
  - `full`: Scope, Watchers, Memory (H-MEM), Investigator and Skeptic loop, Exposure, Playbook, Judge repair loop, human
    approval. About 5-6 min on Nightshift. Explicit `event_id`, `replay_ts` or a `doc_query` different from the question
    always go here, so the evals are stable.
- **Data**: everything is read through **Zetaris** views (`floodsense.gauge_levels`, `eu_watch`, `hazard_now`,
  `weather_forecast`, `exposure_join`, replay seeds). Migrations in `zetaris/migrations` (applied with
  `py tasks.py zetaris-sync`). 45 sources = 26 PEGELONLINE gauges + 11 GloFAS points + 8 Valencia demo points.
- **LLM**: only through the **Nightshift** gateway (`:8088`, `meterless/fast` and `meterless/deep`), Nemotron models.
  `LLM_PROVIDER_SWITCH=true` enables a test-only Anthropic path. **Keep it false for recording and submission.**
  NVIDIA rate-limits (429): `agents/floodsense_agents/nightshift.py` has backoff, a concurrency cap (3) and a pacer (35 rpm).
- **Memory**: H-MEM and World Model in `engines/` (`:8300`). Written only on approval. Demo seeds are labelled `demo-seed`.
- **RAG**: pgvector + NVIDIA NIM `nemotron-3.5-embed-1b`. 25 documents / 1,859 passages (`corpus/`, `scripts/rag_ingest.py`).
- **API** (`api/`, `:18000`): Redis cache, rate limits (10/min, 2 concurrent), SSE events, `GET /system`.
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

### Merged to `main` (all reviewed by an independent agent, CI green)
Router lanes, front door, Europe live watch, forecast lane + DWD ICON weather, live agent pipeline over SSE, mock-style
approval cards, insurer documents and 13 past-flood documents with 59 cited demo memories, demo seed + System page,
NVIDIA backoff, citizen live-first and insurer live-first redesigns, poller container, clarity pass, How it works page.

### Open PRs / branches (pushed to origin, not yet merged). Intended merge order:
1. **#90** `feat/mode-toggle-coherence`: global Live | Past flood switch, Demo data switch, curated Approvals, page purpose
   table. Re-review in progress.
2. **#91** `fix/calm-answers`: deterministic `plain` object and CalmAnswer UI for quick/forecast answers. Round-1 fixes
   pushed (ecf9264), re-review in progress.
3. **#92** `feat/tech-trace`: "How this answer was made" tiles (Zetaris, Nightshift, H-MEM, World Model). Fixes pushed
   (06ddc88). **After #90 and #91 merge**, wire two things: render `<TechTrace run={run} embedded />` inside the calm "Why"
   disclosure when `calmApplies(run)`, and pass `desk.mode` / `desk.eventId` to `LatestRunTechTrace` in `InsurerView.tsx`.
4. `feat/control-tower` (no PR yet): autonomous watch loop + activity feed (`/watch/events`, `/watch/stream`), UI page. Built by
   a background agent; check whether it has been pushed.
5. `feat/operator-desk` (no PR yet): third desk "Civil protection" with a situation board and call-script card.
   Check whether it has been pushed.
Also open and unrelated: #88, #68 (older, from teammates).

Workflow used all day: branch, coding agent, independent review agent, review findings as PR comments, rework, re-review,
CI green, merge, delete branch, update docs and CHANGELOG in every PR. `gh` is at `C:\Program Files\GitHub CLI\gh.exe`;
`gh pr view --comments` fails with this token, so use `gh api repos/<owner>/<repo>/issues/<n>/comments`.

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

## Submission checklist (owner: the humans)
- Deck: `E:\Projects\GenAI-Hackathon-2026\Submission\FloodSense-EU-Pitch-v6.pptx` (needs the new screens), scripts
  `Pitch-Script-v6.md`, `Demo-Video-Script-v6.md`, `Demo-Practice-Checklist.md` in the same folder (outside the repo).
- **Fill in**: Cursor usage details (`docs/SUBMISSION.md`, `TODO(team)`), verify the death tolls on deck slides 2 and 4,
  repo link and prices on the last slide, refresh slide 8 screenshots, update stale speaker notes.
- Before recording: `LLM_PROVIDER_SWITCH=false` in `agents/.env` (and root `.env`) and recreate the agents container.
- Not done and left for the humans on purpose: release tag, making the repo public, recording the video, submitting.
- No ffmpeg on the main dev machine; Higgsfield account has 0 credits. A self-playing HTML walkthrough with captions and
  browser text-to-speech is the planned stand-in for a sample video; the final video should be a real screen recording.

## Next steps, in priority order
1. Merge #90, #91, #92 (order above), then the two follow-up wirings for #92.
2. Review and merge Control tower and operator desk if pushed; otherwise leave them out and say so.
3. Rebuild (`docker compose -p floodsense-app --project-directory . -f compose.yaml -f local/compose.console.yaml --profile rag --profile cache up -d --build agents api ui`),
   run `demo-seed`, then the full e2e on Nightshift (`e2e.py` style: Valencia RAG, Rhine now, live 48 h, Ahr replay,
   replay of first, approve, engines health).
4. Walk every page in both roles and Live / Past / Demo modes in a browser; fix what is confusing or static.
5. Update deck v6 to v7 and the scripts for the new screens (Control tower, operator desk, calm answers, tech trace).
6. Hand the checklist above to the humans for the pre-submission meeting.
