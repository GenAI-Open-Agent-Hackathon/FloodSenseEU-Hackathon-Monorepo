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

- v0.12.0 builds the semantic cache, rate limits, past runs, and the labelled replay drill (Ayush, with Mihir and Zain on the screens).
- The API and the UI share the same two fields. A screen that hides them is a bug.
- Redis in the `cache` Compose profile is available. This ADR does not say the semantic cache must use it.

## Open questions

- TTL for live data versus historical replays. The gameplan says live data has the shorter TTL and does not give numbers.
- The similarity rule for "the same or a very similar query" (Ayush).
- Rate-limit numbers and the global cap on concurrent Nightshift calls (Mihir, v0.12.0).
