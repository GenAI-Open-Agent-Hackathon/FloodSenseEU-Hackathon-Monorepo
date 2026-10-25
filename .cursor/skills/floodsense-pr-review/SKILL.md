---
name: floodsense-pr-review
description: Use when reviewing or fixing a pull request in this FloodSense EU Hackathon-Monorepo (agents, api, ui, data, engines, contracts).
---

# FloodSense PR review

Merge bar for a cloud agent reviewing or fixing a pull request in this monorepo. Check it before editing, and again before calling the PR done.

## Architect-bot reviews

When the architect bot is driving the review:

- Write the findings in chat first. Post them on GitHub after that write-up.
- Edit only the branch named in the task. Leave teammates' branches untouched, and do not open a second PR for the same review.
- `compose.yaml` is architect-owned. Change it only when the task says so.

## Area ownership

Honour the PR's `area:` label and stay inside that folder.

| Label | Stay inside |
| --- | --- |
| `area: agents` | `agents/` |
| `area: api` | `api/` |
| `area: ui` | `ui/` |
| `area: data` | `ingestion/`, `zetaris/`, `pgvector/` |
| `area: engines` | `engines/` |
| `area: contracts` | `contracts/` |

Path owners are in `docs/OWNERSHIP.md`. A `ModelId` or other contract edit belongs on `area: contracts`. From any other area, keep an adapter and a schema test that fails when `contracts/` drifts.

## Merge bar

| Check | Done when |
| --- | --- |
| Code quality | Readable, typed, and small enough to review. No drive-by refactors. |
| Architecture | Open/closed where a new source or lane is likely. YAGNI: no abstraction for a single caller. The diff stays in this area's folder. |
| No hard-coding | Dates, points, timeouts, bounds, thresholds, and model ids live in one shared typed module or env (`.env.example`, `VITE_*`). |
| Contracts | Wire shapes match `contracts/` (JSON Schema plus the Python and TypeScript mirrors), or an adapter plus a schema test covers the gap. |
| Serving honesty | `served_from` is `live`, `cache`, or `replay` (`docs/adr/0006-labelled-cache-and-replay.md`). Cache, replay, and `seed:` rows are never labelled live. An empty API array stays empty. |
| Provenance URLs | Accept and render links only for `http:` and `https:` (`new URL()`). Any other scheme, including `javascript:`, is plain text. |
| Lanes | Show `meterless/fast` or `meterless/deep`. One mapping, in that shared config: fast → `nvidia/nemotron-3.5-lightning-30b-a3b`, deep → `nvidia/nemotron-3-super-120b-a12b` (`docs/adr/0004-nightshift-only-llm-calls.md`). Calls go through Nightshift. The NVIDIA key stays in Nightshift's Providers tab. |
| Tests | Unit tests and fake-based integration tests for the behaviour you changed, wired into `python tasks.py test` (UI tests mean an `npm test` step in that command). `python tasks.py lint` stays green. |
| End to end | Compose-up and browser end-to-end coverage is a follow-up PR unless the task asks for it. |

## Before you finish

- `python tasks.py test` and `python tasks.py lint` pass, or you name the failure that sits outside this area.
- Add a line under `## [Unreleased]` in `CHANGELOG.md`, or write `skip-changelog` in the PR when the notes should omit it.
- No filled `.env`, no `nvapi-` key, no tokens in fixtures, logs, or screenshots.
