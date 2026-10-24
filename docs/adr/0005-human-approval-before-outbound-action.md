# 0005. A human approves every outbound action

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

The agents can recommend what an insurer should do in the next 6–72 hours. Sending that recommendation, or any other outbound action, is not the model's decision.

## Decision

No outbound action runs unless a person approves it. The planned mechanism, already written on the HITL placeholder and in the gameplan, is LangGraph `interrupt()` with a SQLite checkpointer, resumed by the approval API. That code is not built.

The Judge scores claims before the interrupt. It does not approve, delete, or silently rewrite a claim. The human sees the scores and is the final judge. Decisions are approve, edit, and reject. The contract status values are `pending`, `approved`, `edited`, and `rejected`.

An unsupported claim may get one repair round back to Playbook. Otherwise it is flagged.

## Consequences

- v0.8.0 owns the interrupt, the checkpointer, the approval API, and the audit log (Zain, tests with Mihir).
- v0.10.0 puts per-claim Judge scores on the approval payload. The contract already has an optional `judge` object so that payload does not grow a new required field later.
- The UI shows the decision. The channel that would carry an approved action is not selected, and this ADR does not add one.

## Open questions

- Where an approved action is delivered (email, webhook, or something else). Not in the gameplan.
- The Judge score threshold. It stays a proposal until the first eval run (Zain, Mihir).
- Whether `edited` should carry a separate amended body. Today the human text is `note`.
