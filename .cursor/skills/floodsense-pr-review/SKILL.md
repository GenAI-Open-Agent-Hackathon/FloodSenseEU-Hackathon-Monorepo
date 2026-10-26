---
name: floodsense-pr-review
description: Use when reviewing or fixing a pull request in this FloodSense EU Hackathon-Monorepo (agents, api, ui, data, engines, contracts).
---

# FloodSense PR review

Merge bar for a cloud agent reviewing or fixing a pull request in this monorepo. Check it before editing, and again before calling the PR done.

## Architect-bot reviews

When the architect bot is driving the review:

- Write the findings in chat first. Post them on GitHub only after the user approves.
- Edit only the branch named in the task. Leave teammates' branches untouched, and do not open a second PR for the same review.
- `compose.yaml` is architect-owned. Change it only when the task says so.

## Area ownership

Honour the PR's `area:` label and stay inside that folder.

| Label | Stay inside |
| --- | --- |
| `area: agents` | `agents/` |
| `area: api` | `api/` |
| `area: ui` | `ui/` |
| `area: data` | `ingestion/`, `zetaris/`, `pgvector/`, `scripts/zetaris_sync.py` |
| `area: engines` | `engines/` |
| `area: contracts` | `contracts/` |

Path owners are in `docs/OWNERSHIP.md`. A path that is not in this table (`docs/`, `tasks.py`, `.github/`, `evals/`, and the rest) follows that file. A `ModelId` or other contract edit belongs on `area: contracts`. From any other area, keep an adapter and a schema test that fails when `contracts/` drifts.

## Merge bar

| Check | Done when |
| --- | --- |
| Code quality | Readable, typed, and small enough to review. No drive-by refactors. |
| Architecture | Open/closed where a new source or lane is likely. YAGNI: no abstraction for a single caller. The diff stays in this area's folder. |
| No hard-coding | Dates, points, timeouts, bounds, thresholds, and model ids live in one shared typed module or env (`.env.example`, `VITE_*`). |
| Configurable | A teammate can change the demo or scenario without editing many files. Those values stay in one shared module or env, including `ui/src/config/scenario.ts`. |
| Contracts | Wire shapes match `contracts/` (JSON Schema plus the Python and TypeScript mirrors), or an adapter plus a schema test covers the gap. |
| Serving honesty | `served_from` is `live`, `cache`, or `replay` (`docs/adr/0006-labelled-cache-and-replay.md`). Cache, replay, and `seed:` rows are never labelled live. An empty API array stays empty. Zone-less timestamps are treated as UTC. |
| Provenance URLs | Accept and render links only for `http:` and `https:` (`new URL()`). Any other scheme, including `javascript:`, is plain text. |
| Lanes | Show `meterless/fast` or `meterless/deep`. Which model answers a lane today is the one table at the top of `docs/architecture/c4.md` (deep per the c4 table). ADR 0004 points at that table and does not keep a second map. The discontinued `nvidia/nemotron-3-super-120b-a12b` id is not a lane. The schema and ADR 0004 reject it. Calls go through Nightshift. The NVIDIA key stays in Nightshift's Providers tab. |
| Tests | Unit tests and fake-based integration tests for the behaviour you changed. `python tasks.py test` covers api, agents, scripts, contracts, and UI Vitest only. `area: engines` needs `python tasks.py engines-test` (`npm test` and `npm run conformance`, Node.js 22.18 or newer). `python tasks.py lint` stays green. |
| End to end | Compose-up and browser end-to-end coverage is a follow-up PR unless the task asks for it. |

## Before you finish

- `python tasks.py lint` passes. `python tasks.py test` passes for api, agents, scripts, contracts, and UI Vitest, or you name the failure that sits outside this area. Engines are not in that command. `area: engines` also needs `python tasks.py engines-test` (`npm test` and `npm run conformance`, Node.js 22.18 or newer).
- Add a line under `## [Unreleased]` in `CHANGELOG.md`. Omitting that line requires applying the `skip-changelog` GitHub label. Writing the words in the pull request is not enough (`docs/RELEASING.md`, `.github/pull_request_template.md`).
- No filled `.env`, no `nvapi-` key, no tokens in fixtures, logs, or screenshots.
