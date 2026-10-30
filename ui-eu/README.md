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

To serve it at `/eu/` behind the judge login, mount the files into the proxy
(`./ui-eu/web:/srv-eu:ro` in `compose.hosted.yaml`) and add one route in
`deploy/hosted/app.caddy`, before the UI's catch-all `handle`:

    handle_path /eu/* {
        root * /srv-eu
        header Cache-Control "no-store"
        file_server
    }

The UI calls `/api` from the root, so it needs nothing else.
