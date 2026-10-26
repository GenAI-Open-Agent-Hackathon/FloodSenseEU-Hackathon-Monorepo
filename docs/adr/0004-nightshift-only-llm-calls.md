# 0004. Nightshift is the only path for LLM calls

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

Every model call in the demo has to be traceable to a Nightshift routing mode. The NVIDIA provider key is not an application secret.

Corrected 2026-10-25, still Proposed. The first draft named Lightning as the fast lane and the discontinued `nvidia/nemotron-3-super-120b-a12b` id as the deep lane, and said the client was not written.

## Decision

All LLM calls go through one Nightshift client (`agents/floodsense_agents/nightshift.py`). No agent, API handler, or test calls a model vendor directly.

- Base URL from `METERLESS_BASE_URL`, timeout 180 seconds.
- `Authorization: Bearer`, `meterless-app`, and `meterless-scope: user`.
- The app sends routing names, not a vendor model id: fast `meterless/fast`, deep `meterless/deep`. `settings.lane` is the only place that chooses them.
- Who calls which lane, and which model answers today, is the table at the top of [../architecture/c4.md](../architecture/c4.md). This ADR does not keep a second map.
- The demo does not use `meterless/auto`.
- The Judge `model_id` on the shared contract accepts those two routing names, a concrete Nightshift id the reply may carry (`nvidia/nemotron-3.5-super-vl-120b-a12b`, and `nvidia/nemotron-3.5-lightning-30b-a3b` while Lightning stays configured), and `deterministic` when the Judge did not call a model, or when the reply does not parse or has no grounding. In those cases the score stays `deterministic` and does not keep a model id the client returned. The discontinued `nvidia/nemotron-3-super-120b-a12b` id is not in that enum.
- When the reply does carry a grounding, the id the client returned is stored on the Judge score. The API projection keeps it when it is in the enum and omits the judge when it is not. It does not rewrite one id into another.
- The NVIDIA provider key lives only in Nightshift's Providers tab. It is not an env var, a GitHub secret, a fixture, or a Cursor model setting.

## Consequences

- A pull request that adds a model call without the Nightshift client is incomplete.
- CI rejects an `nvapi-` string in tracked files. See [0008](0008-ci-runner-github-hosted.md).

## Open questions

- Whether Nightshift serves embeddings, and which model we use if it does not (Ayush, with Urvashi). `GET /v1/models` has not been recorded here.
- Whether a container can reach Nightshift on `:8088` when that port is bound only to `127.0.0.1` (Ayush, Urvashi).
- The engines sidecar is `engines/` (TypeScript, on main, Ayush). From `v0.9.0` the agents call `ENGINES_URL` when it is set. H-MEM stays behind `FF_HMEM` (default off). Model calls stay on Nightshift. Lane names stay `meterless/fast` and `meterless/deep`.
