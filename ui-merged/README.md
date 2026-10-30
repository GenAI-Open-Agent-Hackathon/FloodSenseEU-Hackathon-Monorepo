# ui-merged

The `ui-eu` plain HTML/CSS/JS interface (Citizen, Insurer, Civil protection) with our 3D map on the three home views. It falls back to Leaflet when WebGL or the bundle fails.

Run (next to the running stack; it only proxies `/api` to the API on the host at port 18000 and joins no network):

    docker compose -p floodsense-merged -f compose.merged.yaml up -d    # http://localhost:15190
    docker compose -p floodsense-merged -f compose.merged.yaml down

Rebuild the map bundle after changing `ui/src/embed` or the map code (output is committed in `web/vendor/`):

    cd ui && npm ci && npm run build:embed

How it works: `ui/src/embed/map3d.tsx` bundles React and the shared `MapShell` as an IIFE exposing `window.FloodMap3D.mount(el, {points, selectedId, onSelect, focusIds})` which returns `{update, destroy}`; `FloodMap3D.pin` builds points with the shared colour rules. `web/js/map3d.js` loads it on demand.

Honesty rules kept: pin colour is the band; the dial fill is relative band order, not a measured value; red only for a live measured gauge above its high water (Germany gauges); model places and insured sites stay amber or grey. Motion stops under `prefers-reduced-motion`. 3D needs internet for OSM, terrain and water tiles.
