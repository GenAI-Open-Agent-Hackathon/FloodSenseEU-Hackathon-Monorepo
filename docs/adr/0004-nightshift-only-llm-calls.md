# 0004. Nightshift is the only path for chat completions

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

Every chat completion in the demo has to be traceable to a Nightshift routing mode. The NVIDIA chat key is not an application secret. Document embeddings are the exception in [0009](0009-vector-search-next-to-zetaris.md).

Corrected 2026-10-25, still Proposed. The first draft named Lightning as the fast lane and the discontinued `nvidia/nemotron-3-super-120b-a12b` id as the deep lane, and said the client was not written.

## Decision

Chat completions go through one Nightshift client (`agents/floodsense_agents/nightshift.py`). No agent, API handler, or test calls a chat-model vendor directly. Document embeddings are not a chat call. They are the [0009](0009-vector-search-next-to-zetaris.md) exception: NVIDIA NIM `POST /v1/embeddings` for `nvidia/nemotron-3.5-embed-1b`, authenticated with `NVIDIA_NIM_API_KEY` from a gitignored env file. That key is not the Providers-tab chat key, and it is not committed.

- Base URL from `METERLESS_BASE_URL`, timeout 180 seconds.
- `Authorization: Bearer`, `meterless-app`, and `meterless-scope: user`.
- The app sends routing names, not a vendor model id: fast `meterless/fast`, deep `meterless/deep`. `settings.lane` is the only place that chooses them.
- Who calls which lane, and which model answers today, is the table at the top of [../architecture/c4.md](../architecture/c4.md). This ADR does not keep a second map.
- The demo does not use `meterless/auto`.
- The Judge `model_id` on the shared contract accepts those two routing names, a concrete Nightshift id the reply may carry (`nvidia/nemotron-3.5-super-vl-120b-a12b`, and `nvidia/nemotron-3.5-lightning-30b-a3b` while Lightning stays configured), and `deterministic` when the Judge did not call a model, or when the reply does not parse or has no grounding. In those cases the score stays `deterministic` and does not keep a model id the client returned. The discontinued `nvidia/nemotron-3-super-120b-a12b` id is not in that enum.
- When the reply does carry a grounding, the id the client returned is stored on the Judge score. The API projection keeps it when it is in the enum and omits the judge when it is not. It does not rewrite one id into another.
- The NVIDIA chat key lives only in Nightshift's Providers tab. It is not an env var, a GitHub secret, a fixture, or a Cursor model setting. `NVIDIA_NIM_API_KEY` is only the document-embedding key.

## Consequences

- A pull request that adds a chat completion without the Nightshift client is incomplete.
- A pull request that embeds documents calls NVIDIA NIM as [0009](0009-vector-search-next-to-zetaris.md) specifies. `NVIDIA_NIM_API_KEY` stays in a gitignored env file. It does not go in the Providers tab and it does not go in a tracked file.
- CI rejects an `nvapi-` string in tracked files. See [0008](0008-ci-runner-github-hosted.md).

## Open questions

- `GET /v1/models` is still the check for the chat lanes. Embeddings are settled in [0009](0009-vector-search-next-to-zetaris.md).
- Whether a container can reach Nightshift on `:8088` when that port is bound only to `127.0.0.1` (Ayush, Urvashi).
- The engines sidecar is `engines/` (TypeScript, on main, Ayush). From `v0.9.0` the agents call `ENGINES_URL` when it is set. H-MEM stays behind `FF_HMEM` (default off). Chat completions stay on Nightshift. Document embeddings stay the [0009](0009-vector-search-next-to-zetaris.md) exception. Lane names stay `meterless/fast` and `meterless/deep`.
