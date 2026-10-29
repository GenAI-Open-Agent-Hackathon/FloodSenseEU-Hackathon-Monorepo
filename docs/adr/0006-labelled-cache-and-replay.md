# 0006. Cached and replayed output is labelled

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

Live Nightshift and Zetaris calls are slow and can fail during the demo. The console still has to show an answer. A cached or replayed answer must not look live, including in the UI, the video, and the deck.

## Decision

Every answer carries `served_from`: `live`, `cache`, or `replay`. When it is not live, `cached_at` is the timestamp of the stored answer. When it is live, `cached_at` is null or omitted. The contract rejects the other combinations.

Only answers that finished and passed the Judge are eligible for the semantic cache. `FF_CACHED_REPLAY` stays off unless a live service fails, in which case the console switches to the recorded run and shows the replay label. The trace keeps the original run's timestamps.

Copy in the UI is a banner such as `cached at HH:MM`, for example "Cached answer from 14:32 · not live · original run R-123".

## Consequences

- v0.12.0 ([#17](https://github.com/GenAI-Open-Agent-Hackathon/FloodSenseEU-Hackathon-Monorepo/pull/17)) ships the semantic cache and the labelled replay drill in the API (Ayush). `FF_SEMANTIC_CACHE` and `FF_CACHED_REPLAY` default off. Past runs were already on main. Rate limits are still a follow-up (Mihir).
- The API and the UI share the same two fields. A screen that hides them is a bug.
- Redis in the `cache` Compose profile is available. This ADR does not say the semantic cache must use it.

## Open questions

- TTL. Closed for the API cache in v0.12.0. Live data expires after `CACHE_TTL_LIVE_S` (900 seconds). A historical replay expires after `CACHE_TTL_REPLAY_S` (86400 seconds). Both are in `api/.env.example`.
- Similarity. Closed for v0.12.0 as folded equality: case, spacing, and punctuation folded, plus the event, customer, replay clock, language, and the agents' flags, lanes, and schema (`api/app/cache.py`). Embedding similarity is still open.
- Rate-limit numbers and the global cap on concurrent Nightshift calls (Mihir). Still open. Not in v0.12.0.
