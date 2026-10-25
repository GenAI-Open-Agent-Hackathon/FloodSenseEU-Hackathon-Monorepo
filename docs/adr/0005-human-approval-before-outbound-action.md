# 0005. A human approves every outbound action

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

The agents can recommend what an insurer should do in the next 6–72 hours. Sending that recommendation, or any other outbound action, is not the model's decision.

## Decision

No outbound action runs unless a person approves it. On main the mechanism is LangGraph `interrupt()` with a SQLite checkpointer, resumed by the approval API. That landed in #4 and is unreleased. `v0.8.0` is not tagged.

The Judge scores claims before the interrupt. It does not approve, delete, or silently rewrite a claim. The human sees the scores and is the final judge. Decisions are approve, edit, and reject. The contract status values are `pending`, `approved`, `edited`, and `rejected`.

An unsupported claim may get one repair round back to Playbook. Otherwise it is flagged.

## Consequences

- The interrupt, the SQLite checkpointer, and the approval API are on main from #4 (Zain). They are not the `v0.8.0` tag.
- v0.10.0 puts per-claim Judge scores on the approval payload. The contract already has an optional `judge` object so that payload does not grow a new required field later.
- The UI shows the decision. The channel that would carry an approved action is not selected, and this ADR does not add one.

## Open questions

- Where an approved action is delivered (email, webhook, or something else). Not in the gameplan.
- The Judge score threshold. It stays a proposal until the first eval run (Zain, Mihir).
- Whether `edited` should carry a separate amended body. Today the human text is `note`.
