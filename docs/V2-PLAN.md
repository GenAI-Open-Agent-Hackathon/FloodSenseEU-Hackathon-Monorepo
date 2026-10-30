# FloodSense EU v2 plan (overnight, 29 to 30 Oct 2026)

Deadline: Nebius x NVIDIA hackathon closes **30 Oct 10:00 PT (19:00 CEST)**. Track: **Best Apps and Agents**.
Base: `main` @ `1598ef9` + PR #107 (LICENSE, docs). Do not move `v1.0.1`.

## Realigned with the 19-hour gameplan (30 Oct)

The team gameplan (Ayush) puts everything under one rule: protect a working demo. Its scope tiers override the backlog below.

- **Must:** Token Factory calls with Nemotron, licence merged, README Nebius section, hosted demo URL, video, Devpost form.
- **Should:** Tavily web evidence (the Skeptic checks it), hosting on Nebius AI Cloud, Token Factory and Tavily tiles in the UI, measured cost and latency.
- **Could:** embeddings on Token Factory, Nemotron Ultra on the deep lane, a Serverless Endpoint.
- **Won't:** new data sources, new pages, the 3D terrain map (#108), big UI changes.
- Feature freeze 17:30 IST (14:00 CEST); submit by 20:30 IST (17:00 CEST); deadline 22:30 IST (19:00 CEST).

Consequences for this plan: the UI redesign branches (design system, desk alignment, agent activity, 3D rivers, insurer density) are on hold; #108 stays open unmerged. The static demo build is dropped (the hosted console in Demo data mode replaces it). The local Postgres backend (#111) is approved but held, since it is a new data path. Added: usage metering and lane check, Skeptic-on-Tavily with UI tiles, hosting kit, submission docs.

## What the rules require (gaps in bold)

| Rule | Today |
|---|---|
| Runtime call to **Nebius Token Factory** (or run on Nebius AI Cloud) | **Missing.** All chat calls go through Meterless Nightshift |
| At least one NVIDIA open model | Have (Nemotron 3.5, NIM embeddings) |
| Public repo, detectable open-source licence | **LICENSE only in PR #107** |
| README: how Nemotron / Token Factory / other Nebius tools are used | **Missing** |
| URL to a working demo or test build | **Missing** (Zetaris is local-only, see risk R1) |
| Demo video under 3 min on YouTube | Human task |
| Feedback on Token Factory / NVIDIA tools (needed for the feedback prize) | **Missing** |
| Text on what was significantly updated in the period | **Missing** |
| Bonus $3,000: functional runtime call to the Tavily API | **Missing** |

Judging (equal weight): technical implementation, design, impact, idea quality.

## Problems found

1. Model calls bypass Nebius (see above). The lane model is already behind one function (`nightshift.complete`), so a second backend is small.
2. The UI hides the agentic backend. Router lanes, Skeptic/Judge verdicts, per-call model, cache hits, rate limits and backoff exist in code (`api/app/cache.py`, `ratelimit.py`, `metrics.py`, `views_cache.py`) but a user only sees them inside a collapsed "How this answer was made" panel.
3. The three desks are inconsistent: different page sets (Citizen 7, Insurer 10, Civil protection 3), different layouts, one shared 1,169-line `global.css`, no single design system.
4. Review's Skeptic/Judge tabs are still the bundled Valencia fixture, not the run.
5. Sites map uses an 80 m3/s band, Replay uses 100 (HANDOVER).
6. First load of live pages takes 5 to 10 s (Zetaris views queried one by one).
7. `POLL_INTERVAL_S=0` busy-loops the poller.
8. Insurer Approvals and Now pages are dense.
9. Stray local files in the repo root (`e2e*.py`, `*.json`, `grep.exe.stackdump`, `ui-mui-3d.patch`, `fetch_run.py`) are untracked; do not commit them.

## Risks

- **R1** Zetaris is a local product, so a hosted demo cannot query it. Plan: host a static "Demo data" build (fixtures, no backend) and also show the local stack in the video. Say so plainly in the submission.
- **R2** A Nebius API key and Tavily key are needed. Both come from the Nebius Builder Program. Until the keys are in `agents/.env`, code ships behind flags with a fake backend and offline tests, and the real call is verified the moment a key exists.
- **R3** Team rule says two APPROVEs before merge. The reviewer agent counts as the independent reviewer, not as a human APPROVE. Mihir or Zain still approves in the morning unless you waive it.
- **R4** UI branches all touch `ui/src/components` and `global.css`. Run them one after another; run backend branches in parallel.

## Backlog (order = priority)

Branch names follow `feat/`, `fix/`, `perf/`, `docs/`. One PR each. Each PR updates `README.md`, the relevant `docs/`, and `CHANGELOG.md` `[Unreleased]`.

### P0: needed to qualify and score

| # | Branch | Work | Done when |
|---|---|---|---|
| 1 | `docs/post-submit-cleanup` (PR #107) | LICENSE, README lead, no TEAM markers | CI green, merged |
| 2 | `feat/nebius-token-factory` | New backend in `agents/floodsense_agents/` for the OpenAI-compatible Token Factory API (`https://api.tokenfactory.nebius.com/v1/`), selected by `LLM_BACKEND=nebius\|nightshift`; fast/deep lane model ids from env (NVIDIA Nemotron models from the Token Factory catalogue); reuse backoff, cache, rate limit, JSON parsing; model id recorded in trace and Judge scores; fake backend for tests | A full-lane run answers through Token Factory, `/system` shows backend and model, unit tests offline |
| 3 | `feat/tavily-context` | Tavily search as a cited source: latest official warnings and news for a place, shown as "Web context" with URL, labelled not-official; used by the Investigator and the citizen "What to do" page; response cached and rate-limited | Runtime Tavily call visible in a run trace; failure degrades to "unavailable" |
| 4 | `docs/nebius-submission` | README section "Nebius and NVIDIA", architecture diagram update, "what changed during the submission period", draft Devpost text, draft Token Factory/NVIDIA feedback, 3-minute video script and shot list | Every required Devpost field has text in `docs/SUBMISSION.md` |
| 5 | `feat/static-demo-build` | `Demo data` mode builds to a static site (no backend), deployable to GitHub Pages or a Nebius Serverless Endpoint; README link | A public URL loads and every page renders from fixtures |

### P1: design and the agentic story (the judges' "Design" and "Impact")

| # | Branch | Work |
|---|---|---|
| 6 | `feat/ui-design-system` | Finish MUI (PR #108): theme, layout shell, shared `PageHeader`, `StatCard`, `StatusChip`, `DataTable`, responsive grid; replace `global.css` rules page by page; keep 375 px no-scroll |
| 7 | `feat/ui-desk-alignment` | One goal per desk and one home page each: Citizen "am I safe, what do I do"; Insurer "which sites are exposed, what do we tell the customer"; Civil protection "which rivers first, what does the hotline say". Same page template, same status words, same top bar; remove pages that repeat another desk |
| 8 | `feat/api-platform-status` | One endpoint with backend, per-lane latency, cache hit rate, rate-limit state, backoff count, model ids (data already in `metrics.py` and `cache.py`) |
| 9 | `feat/ui-agent-activity` | Visible agent layer on every desk: live pipeline (Scope, Watchers, Memory, Investigator, Skeptic, Exposure, Playbook, Judge), per-step model and latency, Skeptic/Judge verdict, approval gate, and a "Platform" strip (backend, cache, rate limit). Replace Review's fixture tabs with the real run |
| 10 | `feat/ui-3d-rivers` | Finish PR #108's map: river lines coloured by status, markers verified with live data, 2D/3D comparison |

### P2: bugs and polish

| # | Branch | Work |
|---|---|---|
| 11 | `fix/gauge-band-consistency` | One threshold definition for Sites map and Replay; Paiporta wording on 29 Oct |
| 12 | `perf/views-first-load` | Query Zetaris views in parallel and prefetch on load |
| 13 | `fix/poller-interval-guard` | Reject `POLL_INTERVAL_S` below a floor |
| 14 | `fix/insurer-density` | Approvals and Now pages: group, collapse, paginate |
| 15 | Review and merge PR #105 (tower scan race), #106 (repo URLs); look at #68, #88 | Needs a human reviewer other than the author |

Stretch, only if time remains: German/Spanish answers; flood history for Saar, Ems, Rhone, Ebro, Tisza.

## Process per branch

1. Coding agent (Sonnet, low effort) on `feat/...` off latest `main`.
2. Docs and CHANGELOG updated in the same branch.
3. Push, open PR.
4. Independent reviewer agent (fresh context, sees only the diff) posts findings as PR comments; the coding agent fixes; the reviewer re-reviews until it has no blocking findings. Every round is a PR comment.
5. End-to-end test on the local Docker stack (`floodsense-app-*` containers are already up): rebuild `api`/`agents`/`ui`, run the e2e script for the lane touched, attach the result to the PR.
6. Merge when CI is green, the reviewer is satisfied and e2e passes. Delete the branch.

## Overnight order

1. #107 and #105/#106 reviews (small, unblock `main`).
2. #2 Token Factory and #3 Tavily in parallel (backend only, separate files); #4 docs after #2.
3. UI serially: #6, #7, #8 and #9 together with #10, then #5.
4. P2 bugs interleaved while a UI PR waits for review.
5. Morning: smoke test of the whole stack, version bump to `v2.0.0` prepared but **not tagged**; Mihir decides.

## What I need from you

- A Nebius Token Factory API key and a Tavily key in `agents/.env` (never in chat or commits), plus the Nemotron model ids you want per lane.
- Whether the reviewer agent plus green CI is enough to merge, or I stop at "approved by reviewer agent" and leave the merge to a human (R3).
