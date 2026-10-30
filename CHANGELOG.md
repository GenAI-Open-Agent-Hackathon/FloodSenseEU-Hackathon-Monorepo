## [Unreleased]


### Added

- Map region focus: `MapShell` `focusIds` flies 2D and 3D (pitch 60, 1.2 to 1.8 s flights) to the gauges of the selected river or place, with a Show full view button; wired in the Europe watch and live sites maps.

Draft notes for a possible 2.0.0 (not released, no tag): [docs/RELEASE-NOTES-v2.0.0.md](docs/RELEASE-NOTES-v2.0.0.md).

- UI: the 3D map is the animated hero. Animated river and canal flow (OpenFreeMap vector tiles, no key) from zoom 8, lakes, sky and fog, and the green blocks are replaced by pulsing gauge pins that open into an animated water dial from zoom 10. Pin colour is the band and the dial fill is band order, never a measured value. Motion stops under `prefers-reduced-motion`.

- UI: the 3D map shows real terrain: free Terrarium elevation tiles (AWS Open Data, no key) drive MapLibre terrain (1.8x exaggeration) and a hillshade layer over the OpenStreetMap tiles, so mountains and river valleys read at a glance.

- UI: the sponsor stack is visible everywhere. A global sponsor strip under the header (Nebius Token Factory, NVIDIA Nemotron with the fast and deep model ids, Tavily with its call count, Zetaris, Meterless H-MEM / World Model), each chip with a status dot from `GET /platform/status` (on, off, or unavailable when the API did not answer) linking to Under the hood. All three desks fill the `agents` slot with `<AgentsLive compact/>` and the `evidence` slot with a Tavily "Web check" card: the Skeptic web verdict in plain words ("A web report supports this", "A web report conflicts with this", "No clear web confirmation"), up to three cited links, the label "Web context, not an official warning" and a "From the latest checked answer" line; the citizen strip is plain (names and dots, no counts or model ids) and the citizen card has words and links only, shown only when the answer is about the selected place, with no numbers, event ids or timestamps; insurer and operator also see status, result count, latency and retrieved time; no run or no web call shows an honest empty state. The Evidence drawer lists web citations with a globe icon and the web-context label; TechTrace shows the real Tavily call (status, results, latency, cached) and a per-lane region next to the cost. Under the hood: model prices per 1M tokens, rate limits, region badge ("EU (Finland)" or "US", never implying EU-only) and cost per answer when `/platform/status` carries them (PR #140), a Tavily card with a web-search activity indicator only while the status is LIVE and Tavily is on, and a "Why each sponsor" list.

- Token Factory pricing and limits: the agents read per-model price, rpm/tpm limits and region from `GET /v1/models?verbose=true` (cached 1 h, never raises, falls back to "price not configured"). `usage` now has `cost_usd` per model, lane and total, `answers`, `cost_per_answer_usd`, `cached_tokens` and a `pricing` block per lane (price per 1M tokens, rpm/tpm, region, country), all passed through `/platform/status` `llm_usage`. The TS parser in `ui/src/api/platform.ts` reads them.

- Nebius pacer defaults follow the published limits: `NEBIUS_RPM` a quarter of the lowest lane rpm (capped at 300), `NEBIUS_MAX_CONCURRENCY` 8 (were 60 and 4, a guess).

- Honesty: the fast lane model (Lightning) runs in Finland (`eu-north1`) but the deep lane model (Super-VL) is listed in the US (`us-north1`); docs no longer imply EU-only inference.

- Tavily run data: each run's API answer carries `web_context` (status ok|empty|unavailable, query built from the place name, n_results, latency_ms, cached, retrieved_at, results url/title/retrieved_at, and the Skeptic `web_check` verdict) in the JSON schema, Python and TS contracts. `/config` and `GET /platform/status` add `tavily_status` (enabled, key_configured boolean, calls, cache_hits, avg_latency_ms, last_status, last_error; never the key). `POST /llm/check` and `python tasks.py check-llm` also run one tiny Tavily search when `FF_TAVILY` is on and report it under `tavily` (not gating).

- Experimental (default off) similar-question cache behind a flag: `EMBEDDINGS_BACKEND=nebius` (default `nim` = unchanged, exact match only) embeds questions with Token Factory `POST /v1/embeddings` (`NEBIUS_EMBEDDING_MODEL`, default `Qwen/Qwen3-Embedding-8B`; 429 backoff and RPM pacing as for chat) and serves a reworded repeat above `EMBED_CACHE_THRESHOLD` (cosine, default 0.90) as a cached answer, labelled `served_from=cache`. Vectors (4096 numbers) are in API process memory only, so no pgvector migration; vectors of another length never match. A hit also needs the same numbers (digits or spelled out in en/de/es/fr) with units, negation or antonym words (contractions, non-/un-, above/below, ...) and place names (all capitalised words plus a place list copied from the agents) in both questions. This guard is a heuristic with known limits (unlisted antonyms, other languages, unlisted lowercase places); false misses are the safe side. The store path also uses the single short attempt, because it runs inside the approval request. Close is wired to API shutdown. Live scores on 30 Oct (4096 dims): 6 paraphrases 0.78 to 0.98 (five at 0.946+), 6 near-misses 0.72 to 0.98, which is why the guard exists and the threshold is 0.90. The lookup path makes one 3 s attempt with no backoff. With the flag on, question text is sent to the Nebius embeddings endpoint. Vectors are per API process: not shared across replicas, lost on restart. The end-to-end cache hit is tested with a mocked transport only. Code: `api/app/embed.py`, `api/app/cache.py`.

- `MapShell` (`ui/src/components/map/`): one shared frame (OSM tiles, attribution, resize) for the event, Europe live, insured sites and gauge maps, with a 2D / 3D toggle saved in `localStorage`. 2D (Leaflet) stays the default and is unchanged. 3D is MapLibre GL, lazy-loaded (separate chunk, no token): tilted view with extruded columns whose height is the band order, amber never red. No terrain and no river lines (no key-free DEM, no river geometry in the views). 3D keeps the live/sample/synthetic labels, draws no column for unknown or missing readings, and falls back to 2D (saved) on WebGL, style or tile failure. 3D not yet checked on a real GPU. `ui/Dockerfile` base is now node:22 (a transitive dependency needs node >= 22). See [docs/architecture/map.md](docs/architecture/map.md).

- UI `<AgentsLive/>` (+ `useAgentsLive` hook): the agent pool in motion with status and duration per agent, handoff animation, revise/repair loops, tool-call chips, cache hit/miss badges and counters, rate-limit lane with Retry-After countdown, model/backend lanes with tokens and latency, and the watch feed. A running run is LIVE; otherwise the newest recorded trace replays on timers, badged REPLAY or SAMPLE. Reduced-motion safe; `compact` variant for desk pages. Mounted on Under the hood and as "Watch the agents" on the Control tower.

- README: one-line Nebius Token Factory + NVIDIA Nemotron lead and a "Judge quick path" section (hosted demo URL still TO FILL). No new screenshots: the built-in browser could only capture 800x500 cropped dark-theme images.

- "Goal and impact" strip (`ImpactStrip`, `lib/impact.ts`) at the top of each desk landing page (Citizen Now, Insurer Now, Operator Situation board): the desk goal, KPI chips from the live hooks ("no data yet" when a source is missing; the insurer book is labelled synthetic) and one cited fact from `docs/DECK-FACTS.md`.

- UI page "Under the hood" (`#/citizen|insurer|operator/stack`): animated cards for Nebius + Nemotron, the agent pool (trace replay with play/pause/speed, SSE follow of a running run), Zetaris, H-MEM + World Model, the Redis cache and rate limiting, each driven by API data and badged LIVE, REPLAY or SAMPLE. CSS-only motion, reduced-motion safe.

- UI: the How this answer was made Nightshift tile reads Nebius Token Factory when /platform/status reports llm_backend=nebius, and shows per-lane Nemotron ids, calls, tokens and cost (price not configured when unset) from run.usage, or Not recorded for this answer; a Platform strip on the System page (backend, lanes, latency p50/p95, cache, rate limit, llm_check, llm_usage).

- Docs: real Token Factory measurements from live runs on 30 Oct 2026 in `docs/SUBMISSION-NEBIUS.md` (lane latency, Ahr and Valencia full-lane time, calls and tokens), updated rules checklist and feedback draft. Cost per run still TO FILL (no official prices retrieved).

- Hosted judge demo kit for a Nebius VM: `compose.hosted.yaml` (ui, api, agents, redis behind a Caddy proxy with basic auth, optional automatic HTTPS, request cap, operator routes blocked), conservative caps (auto-assess off, run rate and concurrency limits, token ceilings), `scripts/hosted_auth.py`, `scripts/smoke_hosted.py` and `docs/DEPLOY-NEBIUS.md` with a cost worksheet (no prices filled in). Runs on the offline Zetaris stand-in (Demo data) with `LLM_BACKEND=nebius`. Validated offline only (compose parse, `caddy validate`); not deployed or run on a real VM.

- Nebius evidence: `python tasks.py check-llm` / `POST /llm/check` (per-lane ok, model id, Nemotron flag, latency), per-run `usage` (tokens, calls, latency per lane and model; optional cost from `NEBIUS_PRICE_PER_M_INPUT/OUTPUT`), `llm_check` and `llm_usage` in `/config` and `/platform/status`, and `NEBIUS_RPM` / `NEBIUS_MAX_CONCURRENCY` for the pacer. Offline-tested only.

- Docs: README section "Built on Nebius and NVIDIA", Token Factory, Tavily and Nebius AI Cloud in the README and C4 diagrams, and `docs/SUBMISSION-NEBIUS.md` (Devpost text, rules checklist, feedback draft, video script, measurements table with TO MEASURE cells).

- `GET /platform/status` (LLM backend, lane models, per-lane p50/p95 latency, cache hit rate, 429 counts, live sources) and `fetchPlatformStatus` in `ui/src/api/platform.ts`.

- Tavily Search as a cited web-context source in the full-lane Investigator (`FF_TAVILY`, default off; `TAVILY_API_KEY`). Snippets are claims labelled "Web context, not an official warning" with a URL citation; digits, markup and newlines are stripped from web text. Live calls are not yet verified against a real key.

- Skeptic `web_check` (one alert-timing claim against fenced web snippets, URL cited, never changes a verdict), a `tavily` trace entry, web citations in the evidence drawer and a Tavily tile in "How this answer was made".

- `LLM_BACKEND=nebius`: optional chat backend on the Nebius Token Factory (OpenAI-compatible API) with NVIDIA Nemotron models, reusing the Nightshift retry, 429 backoff and JSON-mode handling. `nightshift` stays the default. `NEBIUS_API_KEY` is required when selected. `/ready` and `/config` report `llm_backend`. Tested offline with a mock transport only; no live Token Factory call has been made, and the default model ids are unconfirmed against a live `/v1/models`.

- Apache-2.0 `LICENSE` for the FloodSense code (copyright 2026 FloodSense EU contributors). `THIRD_PARTY_NOTICES.md` section 3 updated.

- UI: gauges measured live above their MHW are red in 2D and 3D (red pin with a "!" mark and a faster pulse, ringed 2D marker); model bands stay amber, never red.

### Changed

- UI: Citizen Now, Insurer Now and the Operator Situation board render through one shared `DeskPage` skeleton (impact, head, health, hazard, forecast, map, evidence, actions, agents, footer) with one set of `desk-*` classes. Citizen gets one plain forecast line for Valencia places (for example "Water is rising and may peak around Fri 06:00 CET", in the place's local time, Europe/Madrid for Valencia; or falling, steady, or up slightly; from the trend and 48 h forecast max, no numbers or charts; other places get a one-line note that none is stored); Insurer gets the shared hazard lead, evidence entry and an exposure and approvals block; Operator uses the shared hazard lead and evidence slots. Data fetching and honesty labels are unchanged; the agents slot is empty here.

- `LLM_BACKEND` now defaults to `nebius` (Token Factory), with `NEBIUS_MODEL_FAST=nvidia/Nemotron-3_5-Lightning` and `NEBIUS_MODEL_DEEP=nvidia/Nemotron-3.5-Super-VL`. `LLM_BACKEND=nightshift` is unchanged. Without `NEBIUS_API_KEY`, `/ready` answers 503 naming the fix. The Judge `model_id` allow-list (schema, Python, TypeScript, API copy) also accepts `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b` and `nvidia/nemotron-3-super-120b-a12b`. Hosted token caps raised to 6000/8000. Verified live on 30 Oct (lane check fast 1.1 s, deep 30.4 s; Ahr EMSR517 148 s, 12 calls, 44,569 tokens; Valencia EMSR773 281 s, 14 calls, 40,370 tokens; every claim judged). Tavily live call still unverified.

- Post-submission docs cleanup: README, docs index and "For judges" point at 1.0.1; the tag list shows `v1.0.0` and `v1.0.1`; the Cursor section in README and `docs/SUBMISSION.md` states only what the repository records; living `LLM_PROVIDER_SWITCH` mentions removed from `docs/architecture/technical-highlights.md` and `docs/HANDOVER.md`; the handover reflects the submitted state. Docs only, no code change.

### Fixed

- UI: the 3D map failed to start on the Vite dev server ("Loading Worker ... disallowed MIME type"). The MapLibre worker is now loaded from its asset URL (`setWorkerUrl`) and `maplibre-gl` is excluded from dependency pre-bundling.

- UI: the plain citizen agents block and the 48 h forecast line now show on the Citizen Overview (`#/citizen`), not only on Now; the Operator auto forecast request is documented as the deterministic forecast lane only.

- Agents: Tavily was never called on a normal event run because the Investigator needed `request.context.place`, which demo runs (EMSR773 Valencia, EMSR517 Ahr, via Ask or Approvals) do not carry. With `FF_TAVILY` on and no `context.place`, the search place now comes from the event (EMSR773 -> Valencia, EMSR517 -> Ahr; other events and the watch event make no call), so one cached search runs, the Skeptic `web_check` runs, and `web_context` is filled. A given `context.place` still wins. Web text still supplies no numbers, and the whole-word place match downgrade applies to the derived place.

- First load of live pages: the API prewarms the views cache (`gauge_levels`, `eu_watch`, `hazard_now` and the other live views) in a background task at startup and re-checks it every `VIEWS_PREWARM_INTERVAL_S` seconds (default 120, floor 30, 0 = no refresh), calling a view only near its TTL (Open-Meteo views about once per 600 s) with a doubling failure backoff (cap 1 h). It uses the cache single flight, keeps stale-if-error, never relabels a copy (original `x-query-id` and age stay), and calls views 5 s apart for the Open-Meteo free tier.

- UI model wording follows `llm_backend` from `GET /platform/status`: chips, the run model line, pipeline badges and the How it works box say "Nebius Token Factory" when that is the backend and "Nightshift" only when it is. The Control tower shows a plain sentence for a raw upstream HTTP 429 and keeps the raw text in the Technical detail line. A recorded run that states no provider is shown with its model names only, never with a backend name.

- Insurer Review no longer paints the bundled Valencia sample while it looks up the newest run; the sample shows only when no real run exists and is labelled "Sample, not a real run". Approvals shows "Loading runs" instead of 0 until /runs/past answers, labels live-data runs "Live" (not the event the console had selected) and shows the Exposure policy total when the site count is unknown (the asset sample is capped at 20 rows). Evidence drawer: a Zetaris view citation shows one "Structured data row, no text quote" line instead of two "missing" notes.

- Pegel poller: `POLL_INTERVAL_S` / `--interval` below 30 s (including 0, which busy-looped) is raised to 30 s with a log line.

- One alert line: the insurer Sites map band moves from 80 to 100 m3/s, read from `SIMULATED_ALERT_M3S`, which Replay and the Watchers anomaly line now share (a test fails if they drift). Overview status wording now says "(daily value)", so "Below the 100 m3/s alert line" on 29 Oct is not read as an hourly claim. Still FloodSense's own line, not an official warning.

