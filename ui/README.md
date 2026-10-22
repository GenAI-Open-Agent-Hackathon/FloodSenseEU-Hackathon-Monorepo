# UI: FloodSense EU mock (v2)

> **SAMPLE DATA, with one exception.** Everything in this UI comes from `src/mocks/` and is labelled *Sample* or *Reconstructed sample*, **except** river gauges marked *Live*: those are fetched from the public PEGELONLINE API (German federal waterways) in the browser. Nothing calls the FloodSense API, Zetaris or any model. Quotes are marked `SAMPLE:` and are not real text from the publishers they point to.

This is a clickable mock of the FloodSense EU front end for the Open Agent Hackathon 2026 (Track 02). Its job is to agree on screens and data contracts before the real pipeline (Investigator → Skeptic → LLM-as-a-Judge → human approval) is wired in. If the team adopts it as the real UI, mocks are replaced by real data one `src/api` module at a time (see [Swapping mocks for real data](#swapping-mocks-for-real-data)).

It has two views, switched in the header:

- **Citizen** (`#/citizen`): location search, risk level with a plain-language "why", recommended actions, a real map of river gauges with drill-down and an event replay, nearby gauges, and an "Ask a question" panel with a retrieval trace and a with/without-retrieval comparison.
- **Insurer** (`#/insurer`): exposure KPIs and chart by risk tier, an alert simulation, active alerts, insured sites, the human-in-the-loop approval queue with Judge scores, and the Investigator/Skeptic/Judge reasoning chain.

Every claim carries numbered citation markers. Clicking one opens the evidence panel: URL, title, publisher, access date, section/page/paragraph locator, the (sample) quote with its sha256, the storage policy, and the Zetaris dataset and query that produced the numbers.

## What is new in v2

| Feature | Where | Data |
|---|---|---|
| Real map (Leaflet + OpenStreetMap tiles), region selector (Bavaria, North Rhine-Westphalia, Rhineland-Palatinate, Valencia), coloured markers and legend | Citizen → "River gauges map" | tiles: OSM; markers: see next row |
| Live river gauges from PEGELONLINE inside the region's bounding box, cached 5 min, falling back to sample data if the request fails or times out (10 s); badges say *Live* or *Sample* | same card, footer shows feed status | PEGELONLINE (live); state-portal gauges and Valencia: **sample** (dashed outline) |
| Gauge drill-down: last 48 h, near/warning thresholds, forecast band, citations | click a marker or a gauge in the side summary | observations live (PEGELONLINE) or sample; **forecast band is always sample** |
| Time-slider replay of the Ahr valley (14–15 July 2021) and Valencia (29–30 October 2024): play/pause, 1×/2×/4×/8×, milestones | "Replay: …" buttons on the map card | **reconstructed sample, not real measurements** |
| Alert simulation: threshold crossed → Investigator → Skeptic → Judge → approval queue → human decision → notification | Insurer → "Alert simulation" | sample; uses 1 agent call, plus 1 per decision |
| Header: notification bell with unread count and dropdown (insurer), avatar menu for a fictional demo user (both views), light/dark toggle (both views) | header | sample; no sign-in, no passwords |
| "Why these sources?": every retrieved candidate with relevance, used or discarded with the reason, linked to the citation numbers | under any answer in "Ask a question" | sample retrieval trace |
| With/without retrieval toggle and side-by-side comparison; the no-retrieval answer shows unsupported or contradicted sentences and a failing Judge score | "Ask a question" mode switch | sample; "Compare both" uses 2 agent calls |
| Loading screen shown before the JS bundle arrives, hidden on the first map tile (citizen), on mount (insurer), or after 6 s | `index.html`, `src/lib/splash.ts` | none |
| Light/dark mode | header toggle | follows the OS until you choose, stored in `localStorage` (`floodsense.theme`) |

Other conventions shown in the mock:

- Cached or replayed answers are labelled `cached at HH:MM, expires in N min` and are never shown as live. Ask the same question twice to see it.
- The header shows an agent-call budget (10 calls per minute in the mock). Only agent calls count (asking a question, running the simulation, approving or rejecting); cache hits and gauge data are free.
- Each card's footer names a suggested component area (see below).

## Run it

Needs Node 20 or later.

PowerShell (Windows):

```powershell
cd ui
Copy-Item .env.example .env
npm install
npm run dev
```

bash (macOS, Linux, WSL, Git Bash):

```bash
cd ui
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. Copying `.env` is optional: every variable has a default (see [Environment variables](#environment-variables)).

Other scripts: `npm run lint` (type check), `npm run build` (type check + production build into `dist/`), `npm run preview`.

With Docker, from the repo root: `docker compose up ui`. Compose publishes the dev server on host port **15173** (container port 5173, override with `FLOODSENSE_UI_PORT`), so open http://localhost:15173. Compose reads `ui/.env`, so create it first. The `ui` service depends on `api` (and that on `agents`), so this also builds and starts them and needs their `.env` files; `docker compose up --no-deps ui` starts the UI alone, which is all the mock needs. `VITE_API_URL` defaults to `http://localhost:18000`, which is the API as the browser sees it.

Do not put tokens in the env file. Vite exposes `VITE_*` values to the browser. Zetaris keys and the Nightshift token never go here, and the NVIDIA provider key lives only in Nightshift's Providers tab.

## Environment variables

All optional. Vite exposes `VITE_*` values to the browser, so never put secrets here.

| Variable | Default | Effect |
|---|---|---|
| `VITE_API_URL` | `http://localhost:18000` | FloodSense API base URL (shown in the footer; not called yet) |
| `VITE_MAP_TILE_URL` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Base-map tile template. Must be HTTPS. |
| `VITE_MAP_ATTRIBUTION` | `© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>` | Attribution HTML for the tile provider. Change it together with the URL. |
| `VITE_GAUGE_FEED` | `live` | `mock` never calls PEGELONLINE (offline demos, CI screenshots). |

The tile URL, attribution and "report a map issue" link live in one place: `mapTiles` in `src/api/config.ts`. PEGELONLINE settings (base URL, cache TTL, timeout, licence) are `pegelonline` in the same file.

## Map tiles: OpenStreetMap tile usage policy

The demo uses the public OSM tile server, which is run by volunteers and donations and has a [tile usage policy](https://operations.osmfoundation.org/policies/tiles/). What the code does to follow it:

- **Attribution** is always visible in the map corner: "© OpenStreetMap contributors" linked to the copyright page, plus a "Report a map issue" link. Leaflet's attribution control is never hidden or covered.
- **HTTPS** tile URL `https://tile.openstreetmap.org/{z}/{x}/{y}.png` (no `a/b/c` subdomains).
- **No prefetching or bulk download.** Leaflet loads only the tiles in view; there is no offline cache, no `keepBuffer` increase and no programmatic panning.
- **Normal browser caching.** No `no-cache` headers, no cache-busting query strings, and no restrictive `Referrer-Policy`, so the browser sends its default `Referer` and the tile server can see where requests come from.
- **Light use.** Mouse-wheel zoom is off (click to zoom or use the buttons) and zoom levels are whole numbers, so zooming does not fetch extra fractional levels. Measured with the headless screenshot run (1440×900 window, map about 600×350 px, Bavaria then Rhineland-Palatinate, light and dark): a full walk-through with a cold cache made 73 tile requests (72 from the network); a repeat with a warm cache made 20 requests, all served from the browser's disk cache.

For production or any event with many users, switch to a hosted tile provider (or our own tiles) with an agreement that fits the expected load; it is a change to `VITE_MAP_TILE_URL` and `VITE_MAP_ATTRIBUTION` only. **Decision needed** before a public launch.

In dark mode the tile pane gets a subtle CSS filter (`--map-tile-filter` in `global.css`) so the map is not glaring; markers, tooltips and controls are not filtered. The tiles themselves are the standard OSM style.

## River gauge data: PEGELONLINE and state portals

**PEGELONLINE** (Wasserstraßen- und Schifffahrtsverwaltung des Bundes, WSV), REST API v2, `https://www.pegelonline.wsv.de/webservices/rest-api/v2`:

- Licence: [Datenlizenz Deutschland – Zero – Version 2.0 (DL-DE->Zero-2.0)](https://www.govdata.de/dl-de/zero-2-0). Attribution is not required by the licence; we show the recommended source note "© www.pegelonline.wsv.de" and the licence link in the map footer and in each gauge citation anyway.
- The data are **raw and unchecked** ("Rohdaten, ungeprüft"); the UI says so next to the attribution.
- The browser calls the API directly (it sends `Access-Control-Allow-Origin: *`): one `stations.json` request per region (cached 5 min, concurrent requests share one fetch) and one `measurements.json?start=PT48H` request per opened gauge (cached 5 min).
- PEGELONLINE has no official warning levels in the API. Marker colours use a **proxy** from the characteristic values: red at or above MHW (mean high water), amber from MW + 0.75 × (MHW − MW), grey when no values exist. The UI labels this "proxy threshold, not official warnings". **Decision needed:** replace with official reporting levels per state.
- Federal gauges only cover federal waterways. Smaller rivers (for example the Ahr) are state gauges.

**State portals** (Hochwassernachrichtendienst Bayern, Landesamt für Umwelt RLP, LANUV NRW, SAIH Júcar / CHJ for Valencia) are **sample values only** in this mock (dashed outline on the map, *Sample* badge). **Their licences and terms of use still have to be checked** before any real ingestion, attribution text or caching is built for them.

## Theme (light/dark)

- Colours are CSS custom properties on `:root` in `src/styles/global.css`, with a `:root[data-theme="dark"]` override. Components use only tokens, no hard-coded colours.
- An inline script in `index.html` sets `data-theme` before first paint (no flash): stored choice from `localStorage["floodsense.theme"]`, otherwise `prefers-color-scheme`.
- The header toggle stores the choice; until then the UI follows OS changes (`src/lib/theme.ts`, `src/hooks/useTheme.ts`).

## Folder map

```
ui/
├── index.html                     pre-paint theme script, loading screen
├── package.json, package-lock.json, tsconfig.json, vite.config.ts
├── Dockerfile, .dockerignore, .env.example
├── scripts/gen-citations.mjs      regenerates quote hashes in src/mocks/citations.ts
└── src/
    ├── main.tsx, App.tsx          entry point, app shell, hash routing
    ├── types/                     typed contracts shared by UI and (later) API; index.ts re-exports all
    ├── mocks/                     SAMPLE data only; imported by src/api, never by components
    ├── api/                       data-access layer
    │   ├── client.ts              the ONLY module components import data from
    │   ├── citizen.ts, citations.ts, gauges.ts, replay.ts,
    │   │   insurer.ts, simulation.ts, notifications.ts, session.ts
    │   │                          one function per data need (mock bodies today)
    │   ├── pegelonline.ts         PEGELONLINE client and mapping (live)
    │   ├── mockTransport.ts       simulated latency for mock responses
    │   ├── ttlCache.ts            small TTL cache with in-flight de-duplication
    │   ├── rateLimiter.ts         agent-call budget
    │   └── config.ts              env vars, map tiles, PEGELONLINE settings
    ├── hooks/                     useAsync, useStore, useHashRoute, useNow, useTheme,
    │                              useReplayPlayer, useDismiss
    ├── lib/                       pure helpers: formatting, gauge status, theme, splash, stores
    ├── components/
    │   ├── shared/                header, cards, badges, cache label, rate limit, sparkline
    │   ├── header/                theme toggle, notification bell, profile menu
    │   ├── citations/             citation markers, cited claims, evidence panel
    │   ├── map/                   Leaflet map, gauge map, drill-down, chart, replay, legend
    │   ├── citizen/               citizen view, ask panel, retrieval trace
    │   └── insurer/               insurer view, alert simulation, approval queue
    └── styles/global.css          plain CSS, design tokens at the top
```

Run `node scripts/gen-citations.mjs` after editing sample quotes so their sha256 values stay correct.

## Swapping mocks for real data

Rules that keep each swap to one file:

1. Components import data **only** from `src/api/client.ts`. They never import `src/mocks/` or another `src/api/*` module. (Check: `grep -rn "mocks/\|api/[a-z]" src/components` should only show `api/client`.)
2. Each data need is one async function with a typed result from `src/types/`. A swap replaces the function body in its module (for example `respond(sampleX)` → `fetch(`${apiBaseUrl}/…`)`) and keeps the signature. Components, hooks and types do not change.
3. Provenance travels with the data (`provenance: "live" | "sample" | "reconstructed"`, `fallbackReason`). A real implementation sets it to `live`, and the *Sample* badges disappear on their own.
4. Agent calls go through `rateLimiter.ts` (`consumeRequest()` before the request). Keep that when swapping, or move the budget to the server and update `subscribeRateLimit` from response headers.

"A → B" means view A loads the data and passes it to B as props; B itself has no data access.

| Component(s) | `src/api/client` function(s) | Implemented in | Source today | Real source (to agree) |
|---|---|---|---|---|
| `CitizenView` → `LocationPicker` | `listLocations` | `api/citizen.ts` | sample | FloodSense API (geocoding/locations) |
| `CitizenView` → `RiskSummary`, `RecommendedActions` | `getRiskAssessment` | `api/citizen.ts` | sample | FloodSense API (Investigator → Skeptic → Judge result, cached) |
| `CitizenView` → `GaugeList` ("Gauges near …") | `getGauges` | `api/citizen.ts` | sample | ingestion service (state portals + PEGELONLINE) |
| `AskPanel` | `askQuestion`, `listSuggestedQuestions` | `api/citizen.ts` | sample (rate-limited) | FloodSense API (agentic RAG + answer cache) |
| `RetrievalTraceView` | `Answer.retrieval` from `askQuestion`; `getCitations` for the markers | `api/citizen.ts` | sample | retrieval step of the RAG pipeline |
| `CitedClaims` (→ `CitationMarker`, `CitationPanel` via `CitationContext`) | `getCitations` | `api/citations.ts` | sample (+ generated for live gauges) | citation store (ingestion) |
| `CitizenView` (`listRegions`, `getDefaultRegionId`) → `GaugeMap`, `RegionSelector`, `RegionSummary` (`getRegionGauges`) | `listRegions`, `getDefaultRegionId`, `getRegionGauges` | `api/gauges.ts` | **live** PEGELONLINE + sample state gauges | PEGELONLINE via backend or ingestion; state portals after licence check |
| `GaugeDrilldown`, `LevelChart` | `getGaugeObservations`, `getGaugeForecast` | `api/gauges.ts` | observations **live** or sample; forecast sample | observations: PEGELONLINE / state portals; forecast: forecasting service (to agree) |
| `ReplayControls`, `ReplayDrilldown`, `GaugeMap` replay mode | `listReplayScenarios`, `getReplayScenario` | `api/replay.ts` | reconstructed sample | eval-set archive of historic measurements (licence to check) |
| `InsurerView` → `ExposureKpis`, `TierExposureChart`, `SiteTable` | `listPortfolioSites` | `api/insurer.ts` | sample | Zetaris federated query via API |
| `InsurerView` → `AlertList` | `listAlerts` | `api/insurer.ts` | sample | FloodSense API alerts |
| `ApprovalQueue`, `InsurerView` | `approvals` (store), `decideApproval` | `api/insurer.ts` | sample, in-memory | LangGraph HITL interrupt/resume via API; store updated by polling or SSE |
| `InsurerView` → `ReasoningChainView` | `getReasoningChain` | `api/insurer.ts` | sample | LangGraph run trace |
| `AlertSimulation` | `startAlertSimulation`, `submitSimulatedApproval` | `api/simulation.ts` | sample script | demo endpoint that triggers a real run (or keep as demo only) |
| `NotificationBell` | `notifications` (store), `markNotificationsRead` | `api/notifications.ts` | sample, in-memory | notification service (SSE/WebSocket) |
| `ProfileMenu` | `getCurrentUser` | `api/session.ts` | fictional demo users | auth/session (not designed yet) |
| `RateLimitIndicator` | `getRateLimitSnapshot`, `subscribeRateLimit` | `api/rateLimiter.ts` | client-side budget | server rate-limit headers |
| `LeafletMap` | `mapTiles` | `api/config.ts` | OSM public tiles | hosted tile provider (decision needed) |

## Suggested areas

These are suggestions to discuss, not assignments. The card footers ("Component area: …") use the same names.

| Person  | Suggested area | Where it shows up in the mock |
|---------|----------------|-------------------------------|
| Mihir   | Architect: contracts in `src/types/`, overall flow | all views |
| Urvashi | Zetaris federation | Zetaris query and dataset in the evidence panel, exposure figures |
| Saleeta | Ingestion and citations | gauges, source locators, quotes and hashes, storage policy |
| Ayush   | Memory, embeddings and cache | cache labels, "Ask a question" answers |
| Zain    | LangGraph, HITL and Judge, then UI | approval queue, Judge scores, reasoning chain |

Anyone who finishes a slot early can pick up UI work. Announce it at stand-up.
