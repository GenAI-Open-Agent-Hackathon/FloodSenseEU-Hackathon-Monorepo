# 0007. JSON Schema is the shared contract

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

The agents, the API, and the UI all need the same citation, claim, answer, and approval JSON. The mock on `spike/mock-ui` has TypeScript types in camelCase. That branch is not merged. The gameplan already wrote the citation columns, the Judge output, and `served_from` / `cached_at` in snake_case.

Generating types from Pydantic, or generating Pydantic from TypeScript, needs a tool the whole team must remember to run. The set of types for v0.2.0–v0.8.0 is small.

## Decision

`contracts/schemas/floodsense.schema.json` is the source of truth (JSON Schema draft 2020-12). Python (Pydantic) and TypeScript are hand-checked mirrors. Example payloads in `contracts/examples/` must validate against the schema and parse with the models. `python tasks.py test` runs those checks. `python tasks.py lint` typechecks the TypeScript.

No generator. A new field is a schema edit, both mirrors, an example, and a note at the 14:00 check-in.

In scope: claim, citation, evidence, answer, playbook action, approval, and the Judge result. Judge scores are optional on the answer and the approval until v0.10.0. Wire names are snake_case. `additionalProperties` is false except for evidence rows, whose columns are not fixed.

Out of scope until an owner proposes the fields: gauges, portfolio and exposure columns, Skeptic challenge records, retrieval traces, notifications, and the mock's risk enum. Details are in [contracts/README.md](../../contracts/README.md).

`agents/`, `api/`, and `ui/` do not import the package yet.

## Consequences

- The mock's camelCase types and its Judge rubric (`verdict`, `contradicted`, `skepticResolution`) are not the wire format.
- Layer `c` is a legal citation layer now, and the feature stays behind `FF_RAG_DOCS`.
- Drift shows up as a failed test instead of a failed demo.

## Open questions

- Required citation fields per layer, after the real source columns are known (Urvashi, Saleeta).
- Closing `model_id` to the two pinned lanes. This ADR does that. Ayush can reopen it if a lane id changes.
- Whether a numeric claim must include an evidence row. The schema allows an empty evidence list.
