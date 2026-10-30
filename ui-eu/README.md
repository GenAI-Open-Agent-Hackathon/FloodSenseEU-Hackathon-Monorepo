# ui-eu

A second interface for FloodSense EU on the same API, in plain HTML, CSS and
JavaScript with no build step. Live at https://floodsense-eu.zaindroid.me.

Each role gets its own home and Ask:

- **Citizen**: search a place, a plain sentence and a level dial, what to do,
  and a chat for questions.
- **Insurer**: an exposure desk with dials, a map of insured sites, the
  largest exposures and the actions waiting for sign-off.
- **Civil protection**: an operations board with a map coloured by state, the
  highest river, a countdown to the next check, the act-first queue and the
  watch feed.

Watch, Ask (with the live pipeline at the bottom) and Decide (sign-off) work
for every role, in light and dark themes.

## Run it

Next to the dev stack, on the same API:

    docker compose -f compose.yaml -f compose.eu.yaml up -d

Then open http://127.0.0.1:15180. `ui-eu/Caddyfile` serves the files and
forwards `/api/*` to the API with the prefix stripped, the same contract as
`ui/` (`VITE_API_URL=/api`).

## On the hosted demo

`compose.hosted.yaml` mounts `ui-eu/web` into the proxy, and
`deploy/hosted/app.caddy` serves it at `/eu/`, behind the same judge login as
`ui/`. The proxy's `/api` route is shared, so nothing else changes.

## Using it as the main UI

The two interfaces are interchangeable: both call the same API at `/api` and
neither needs the other.

- **Hosted, at `/`:** in `deploy/hosted/app.caddy`, point the catch-all
  `handle` at `/srv-eu` instead of `/srv`, and drop the `try_files` line
  (ui-eu routes with `#/...`, so it needs no SPA fallback). `ui/` can then
  move to its own path, or come out of the proxy image.
- **Dev, on its own:** `compose.eu.yaml` already runs it; the `ui` service is
  not needed for it.

What it calls, all on `/api`:

| Endpoint | Used for |
|---|---|
| `GET /views/gauge_levels`, `/views/eu_watch`, `/views/hazard_now` | places and their state |
| `GET /views/exposure_join` | insured sites (insurer) |
| `GET /watch/status`, `/watch/events` | the watch loop, next check, feed |
| `GET /platform/status` | model backend and Tavily |
| `POST /runs?wait=false`, `GET /runs/{id}`, `/runs/{id}/events` (SSE), `/runs/past` | Ask and the live pipeline |
| `POST /runs/{id}/approval` | Decide (sign-off) |

Ask sends `context: {role, page: "ask", place}` with `role` one of `citizen`,
`insurer` or `operator`, so answers are worded for that reader.
