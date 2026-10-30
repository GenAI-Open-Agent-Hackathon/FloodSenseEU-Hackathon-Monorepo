# FloodSense EU v2.0.0 release notes

**DRAFT. Not released.** No tag, no GitHub Release and no version bump exists for 2.0.0. The owner decides whether and when to cut it (steps in [RELEASING.md](RELEASING.md)). Everything below is taken from `CHANGELOG.md` [Unreleased], `git log v1.0.1..origin/main` and [SUBMISSION-NEBIUS.md](SUBMISSION-NEBIUS.md), as of 30 Oct 2026.

## What changed since v1.0.1

### LLM backend: Nebius Token Factory with NVIDIA Nemotron
- `LLM_BACKEND` now defaults to `nebius`. Fast lane `nvidia/Nemotron-3_5-Lightning`, deep lane `nvidia/Nemotron-3.5-Super-VL`. `LLM_BACKEND=nightshift` is unchanged.
- The Judge `model_id` allow-list also accepts `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b` and `nvidia/nemotron-3-super-120b-a12b`. Hosted token caps are 6000/8000.
- Verified live on 30 Oct 2026 (figures from `SUBMISSION-NEBIUS.md` section 6; local Docker, Zetaris live data):
  - Lane check, one tiny completion each: fast 1,108 ms, deep 30,399 ms (the deep model reasons).
  - Ahr 2021 (EMSR517), full lane: 148 s, 12 calls, 44,569 tokens.
  - Valencia 2024 (EMSR773), full lane: 281 s (ran concurrently with the Ahr run), 14 calls, 40,370 tokens.
  - Every model-judged claim was judged. Only the lane check and these two replays were run live. Cost per answer is not computed: no official price was retrieved.
- Usage metering and lane check: `python tasks.py check-llm` / `POST /llm/check`, per-run `usage` (tokens, calls, latency per lane and model), `llm_check` and `llm_usage` in `/config`, `NEBIUS_RPM` / `NEBIUS_MAX_CONCURRENCY` for the pacer.

### Web evidence
- Tavily Search as cited web context in the full-lane Investigator and a Skeptic `web_check` (`FF_TAVILY`, default off, needs `TAVILY_API_KEY`). Snippets are labelled "Web context, not an official warning". **Not verified against a live Tavily key.**

### Platform and hosting
- `GET /platform/status` (backend, lane models, p50/p95 latency, cache hit rate, 429 counts, live sources).
- Hosted judge-demo kit for a Nebius VM (`compose.hosted.yaml`, Caddy proxy with basic auth, caps, `scripts/smoke_hosted.py`, [DEPLOY-NEBIUS.md](DEPLOY-NEBIUS.md)). Validated offline only; not deployed to a real VM.

### UI
- "Under the hood" page per desk (`#/citizen|insurer|operator/stack`), one live-data card per technology, badged LIVE, REPLAY or SAMPLE.
- Goal and impact strip on each desk landing page.
- Token Factory tile in "How this answer was made"; Platform strip on the System page.
- Backend-aware wording (Nebius Token Factory vs Nightshift) and a plain sentence for an upstream 429.

### Fixes
- Review: newest full run, no pinning by `VITE_REPLAY_RUN_ID`, labelled sample fallback. Approvals: "Loading runs" state, "Live" labels, policy count.
- Pegel poller interval floored at 30 s.
- One alert line (100 m3/s) shared by Sites map, Replay and Overview.
- Honest impact chips; cited facts quoted verbatim from `DECK-FACTS.md`.

## Known limitations
- Tavily live call unverified.
- Hosted kit not run on a real VM.
- Not on `main` (open pull requests on 30 Oct, so not part of this release): #108 MUI design system and 3D terrain map, #111 local Postgres data backend, #120 model provider naming per call, #88 recorded-run walkthrough, #68 Skeptic one-view-per-statement.
- Earlier limits in [RELEASE-NOTES-v1.0.0.md](RELEASE-NOTES-v1.0.0.md) still apply (modelled river data is not an official warning, synthetic insurer portfolio, English only).

## Upgrade notes
- **`LLM_BACKEND` default changed to `nebius`.** A fresh clone needs `NEBIUS_API_KEY`, or `LLM_BACKEND=nightshift` in `agents/.env`. Without a key `/ready` answers 503 naming the fix.
- Optional: `TAVILY_API_KEY` with `FF_TAVILY=true`; `WATCH_ADMIN_TOKEN` for the hosted kit.
