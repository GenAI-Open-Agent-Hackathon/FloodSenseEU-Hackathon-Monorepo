# 0004. Nightshift is the only path for LLM calls

- Status: Proposed
- Date: 2026-10-22
- Updated: 2026-10-24
- Owner: Mihir

## Lane mapping

As of 24 Oct 2026. A future model change only edits this table. Other docs name the routing modes and link here.

| Routing name | Model |
| --- | --- |
| `meterless/fast` | `nvidia/nemotron-3.5-lightning-30b-a3b` (Nemotron 3.5 Lightning 30B A3B) |
| `meterless/deep` | `nvidia/nemotron-3.5-super-vl-120b-a12b` (Nemotron 3.5 Super VL 120B A12B) |

Nemotron 3 (`nvidia/nemotron-3-super-120b-a12b`) was the deep lane. It was discontinued and replaced by the `meterless/deep` row.

## Context

Every model call in the demo has to be traceable to a pinned NVIDIA Nemotron lane. The NVIDIA provider key is not an application secret.

The application asks Nightshift for a routing mode (`meterless/fast` or `meterless/deep`). Nightshift picks the model.

## Decision

All LLM calls go through one Nightshift client. No agent, API handler, or test calls a model vendor directly.

- Base URL from `METERLESS_BASE_URL`, timeout 180 seconds.
- `Authorization: Bearer`, `meterless-app`, and `meterless-scope: user`.
- Fast lane: `meterless/fast` (Watchers).
- Deep lane: `meterless/deep` (Investigator, Playbook, Judge).
- The demo does not use `meterless/auto`. The Judge `model_id` enum in the contract is unchanged. It still lists vendor model ids, including the discontinued Nemotron 3 id named above. Aligning that enum is a separate contract change.
- The model id that answered is logged on the trace.
- The NVIDIA provider key lives only in Nightshift's Providers tab. It is not an env var, a GitHub secret, a fixture, or a Cursor model setting.

The client is not written yet. This ADR does not choose the Python package that will wrap the HTTP call.

## Consequences

- A pull request that adds a model call without the Nightshift client is incomplete.
- CI rejects an `nvapi-` string in tracked files. See [0008](0008-ci-runner-github-hosted.md).

## Open questions

- Whether Nightshift serves embeddings, and which model we use if it does not (Ayush, with Urvashi). `GET /v1/models` has not been recorded here.
- Whether a container can reach Nightshift on `:8088` when that port is bound only to `127.0.0.1` (Ayush, Urvashi).
- Python in-process engines, or a TypeScript sidecar, for H-MEM and World Model (Ayush). `engines/` is not created.
