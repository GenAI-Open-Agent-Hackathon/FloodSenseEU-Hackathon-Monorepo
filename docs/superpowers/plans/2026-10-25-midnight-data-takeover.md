# Midnight Data Takeover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Urvashi + Saleeta Zetaris/ingestion work onto Mihir-owned PRs from `feat/ingestion-sources-terms`, verify on Mihir's laptop, then wire UI + LangGraph + Ayush lanes so FloodSense can leave `v0.0.0` toward live-data increments by midnight CET Sun 25 Oct 2026.

**Architecture:** Do not push onto Urvashi's `feat/zetaris-data-sync`. Fork Mihir-owned branches from Saleeta tip `feat/ingestion-sources-terms` @ `cc2f414` (superset of Urvashi's migrations + live feeds 030–033). Split into mergeable PR waves; each wave gets dual review (floodsense-pr-review) before merge; laptop `zetaris-sync` + `verify` between waves. Close draft PR #12 as superseded after Wave A opens.

**Tech Stack:** Zetaris Lightning SQL migrations, `scripts/zetaris_sync.py`, Python stdlib feeds, FILESTORE CSVs under `ingestion/prep`, `contracts/` view contracts, GitHub PRs, docker compose (Mihir-owned), FastAPI/UI/LangGraph consumers later.

## Global Constraints

- Repo: `https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo`
- Base tip for data waves: `feat/ingestion-sources-terms` (Saleeta), rebase onto current `main` before each PR
- Do **not** push commits onto `feat/zetaris-data-sync` or Saleeta's remote branch; open new `feat/data-*` / `chore/ownership-*` branches under Mihir
- Area labels: `area: data` for ingestion/zetaris; `area: contracts` if touching contracts; Mihir owns `compose.yaml` — teammates do not edit it
- Model lanes in docs/UI: `meterless/fast` and `meterless/deep` only (mapping table once at top)
- Cached/seed/replay must never be labelled live
- Show PR review findings to Mihir in chat before posting on GitHub
- Merge style: normal merge commits into `main` (not squash/rebase)
- Midnight CET is the soft freeze for data blockers; UI/agents wire starts only after Wave A+B verify green on laptop
- Tests: unit tests for sync/contracts via `python tasks.py test` / pytest under `scripts/tests`; live Zetaris verify only on Mihir laptop (has local Zetaris)

## File map (existing on Saleeta tip — reuse, do not rewrite blindly)

| Path | Role |
| --- | --- |
| `scripts/zetaris_sync.py` | Apply / status / verify migrations |
| `scripts/tests/test_zetaris_sync.py` | Unit tests for sync |
| `scripts/tests/test_migration_contract.py` | Headers ↔ seed ↔ contract |
| `zetaris/migrations/001–007, 010–017` | Core GloFAS/rain + seed + exposure/provenance |
| `zetaris/migrations/030–033` | Live REST + live FILESTORE feeds |
| `ingestion/prep/*` | EMS/OSM/portfolio/provenance/valencia CSVs + prep scripts |
| `ingestion/feeds/feeds.py` | Live feed pull/check/stage |
| `docs/legal/sources.md` | Licence / attribution |
| `docs/OWNERSHIP.md` | Path owners — transfer zetaris to Mihir |
| `contracts/` | Need `views.yaml` if missing on main (create in Wave A) |

## PR wave order

| Wave | Branch (new) | Increment | Merge gate |
| --- | --- | --- | --- |
| A | `feat/data-v010-sync-seed` | v0.1.0 | CI green + dual review + laptop sync+verify discharge+seed |
| B | `feat/data-v030-exposure-provenance` | v0.3.0 core | CI + review + verify exposure/provenance |
| C | `feat/data-live-feeds` | live feeds | CI + review + feeds check + staging docs |
| D | `chore/ownership-zetaris-mihir` + PEGELONLINE | ownership + gauges | OWNERSHIP.md + spike #7 fold or follow-up |
| E | UI + agents wire | after data green | separate PRs: UI seed-label fix, agents strip-UI, FF_LIVE_DATA |

---

### Task 1: Save this plan + ownership note in repo

**Files:**
- Create: `docs/superpowers/plans/2026-10-25-midnight-data-takeover.md` (this file)
- Modify later in Task 5: `docs/OWNERSHIP.md`

- [ ] **Step 1:** Commit this plan on Wave A branch (or a tiny chore branch if Wave A is already open).
- [ ] **Step 2:** Comment on PR #12 that Mihir-owned wave supersedes; do not merge #12 as-is.

### Task 2: Wave A — v0.1.0 sync + GloFAS + seed (BLOCKING)

**Files (carry from Saleeta tip, trim scope):**
- Keep: `scripts/zetaris_sync.py`, `scripts/tests/test_zetaris_sync.py`, `scripts/tests/test_migration_contract.py`
- Keep migrations: `001`–`004`, `011`–`012` (minimum for v0.1). Prefer keeping `005`–`007` and `010`, `013` if already green on tip — do **not** delete working migrations; if CI noise, document deferred verify for later views in PR body rather than deleting Saleeta/Urvashi files.
- Create if missing: `contracts/views.yaml` matching `-- view:` / `-- columns:` / `-- min_rows:` headers for `floodsense.discharge_daily` and `floodsense_seed.discharge_daily` (and other views present in kept migrations)
- Modify: `scripts/zetaris_sync.py` so successful `sync` **runs `verify` before exit 0** (or `tasks.py zetaris-sync` chains verify). "Already exists" skips must still be followed by verify for declared views.
- Modify: `ingestion/prep/stage_local_zetaris.py` + README so a cold laptop can stage seed CSVs before migration `010`
- Modify: `docs/OWNERSHIP.md` — set `/zetaris/`, `/scripts/zetaris_sync.py`, `/ingestion/` primary owner to Mihir (Saleeta secondary on ingestion prep/demo); note takeover date 2026-10-25

**Interfaces:**
- Consumes: Saleeta tip tree; `ingestion/.env` with `ZETARIS_API_KEY`, `ZETARIS_REST_URL`, `ZETARIS_ORG_ID`
- Produces: PR merging sync+migrations so agents can `SELECT` from `floodsense_seed.discharge_daily` offline and `floodsense.discharge_daily` when live

- [ ] **Step 1:** Create branch from `feat/ingestion-sources-terms`, rebase onto `main`, resolve conflicts favoring Saleeta tip for data files and main for unrelated CI/docs unless data-specific.
- [ ] **Step 2:** Add failing test that `cmd_sync` / `tasks.py zetaris-sync` returns non-zero when verify would fail (mock client); then implement sync→verify chain.
- [ ] **Step 3:** Ensure `contracts/views.yaml` exists and `test_migration_contract.py` passes.
- [ ] **Step 4:** Document cold-start: copy `.env.example` → `.env`, stage CSVs, `python tasks.py zetaris-sync`, `python scripts/zetaris_sync.py verify`.
- [ ] **Step 5:** Open PR titled `feat(data): v0.1.0 Zetaris sync, GloFAS discharge, seed views` with label `area: data`, body listing laptop verify steps. Assign Mihir; mention @urvashi07 @saleeta for credit.
- [ ] **Step 6:** Run unit tests: `python -m pytest scripts/tests/ -q` (or `python tasks.py test` if that covers them). Expected: PASS.
- [ ] **Step 7:** Stop for dual independent review (parent launches reviewers). Do not merge until Mihir approves posted review + laptop verify.

### Task 3: Laptop verify Wave A (Mihir machine — parent coordinates)

**Not a cloud agent.** Parent uses ListMachines / approved Shell on Mihir laptop.

- [ ] **Step 1:** Confirm Zetaris up on `:8888`, `ingestion/.env` present.
- [ ] **Step 2:** Stage seed CSVs if needed; run `python tasks.py zetaris-sync` then `python scripts/zetaris_sync.py verify`.
- [ ] **Step 3:** Spot-check `SELECT COUNT(*) FROM floodsense_seed.discharge_daily` and live `floodsense.discharge_daily` if network allows.
- [ ] **Step 4:** Report OK/FAIL to Mihir; only then merge Wave A.

### Task 4: Wave B — exposure + provenance + prep CSVs (v0.3.0)

**Files:** migrations `010`, `014`–`017` (and any remaining from A), `ingestion/prep/*`, provenance rows, `docs/legal/sources.md` updates for any new sources cited.

- [ ] Branch from main (after A merge) or continue stacked branch; open PR `feat(data): exposure_join, provenance, seed twins`.
- [ ] Ensure live `exposure_join` / `provenance` document FILESTORE backing honestly (not fake "live EMS API").
- [ ] Tests + dual review + laptop verify those views.

### Task 5: Wave C — live feeds 030–033 + feeds.py

**Files:** `ingestion/feeds/feeds.py`, migrations `030`–`033`, feeds README, `.env.example` keys (`AEMET_API_KEY` optional).

- [ ] Add provenance/licence rows for DWD + PEGELONLINE before citing in demo.
- [ ] PR `feat(data): live feed tables and feeds.py pull/stage`.
- [ ] Dual review; laptop `python ingestion/feeds/feeds.py check` (network).

### Task 6: Wave D — ownership + PEGELONLINE

- [ ] PR updating `docs/OWNERSHIP.md` if not done in A; fold useful bits from `spike/zetaris-live-gauges` (#7) or close spike with pointer to Wave C pegel table.
- [ ] Mihir remains compose owner; no compose edits by data agents without ask.

### Task 7: Wave E — wire UI + LangGraph + Ayush (after data green)

Depends on Waves A–B merged (C nice-to-have for true multi-source live).

- [ ] Fix PR #13 seed-still-labelled-live (reviewer B); dual review before post.
- [ ] Coordinate Zain #4: strip ui/desk, async httpx, contracts, live labelling — do not edit Zain's branch; new Mihir branch or ping Zain.
- [ ] Wire UI to API runs + `FF_LIVE_DATA`; consume Ayush engines/lanes from his merged PRs (#9/#15/#16/#17) — rebase/merge order: engines → agents memory → API cache → UI.
- [ ] Tag increment(s) on green main (`v0.1.0` after A, `v0.3.0` after B) with release notes.

## Out of scope tonight

- Full eval set / RAG docs (`v0.11.0`)
- Demo video / PPT (Saleeta)
- Enforcing GitHub branch protection (org is Free)

## Success criteria (midnight)

1. Mihir owns zetaris/sync in OWNERSHIP.md
2. At least Wave A merged (or merge-ready + laptop verify green)
3. Agents can query seed views; live GloFAS path documented and verified once
4. PR #12 closed/superseded with link to Wave A
5. UI/agents wire PRs opened or queued with clear dependency on data

