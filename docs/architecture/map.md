# Map: one shell, two views

All four UI maps (event replay in `MapPanel`, Europe live watch in `EuWatch`, insured sites in `LiveSitesMap`, river gauges in `GaugeMap`) render through `ui/src/components/map/MapShell.tsx`. The shell owns the OpenStreetMap tiles, the attribution, resize handling and a 2D / 3D toggle above the map. Each map keeps its own markers, tooltips, selection callbacks, legend and date slider; the shell only gives it a Leaflet map (`onMap2d`) or, in 3D, normalized points.

- **2D (default):** Leaflet, unchanged behaviour. The choice is saved in `localStorage` (`floodsense.mapMode`, read in try/catch) and shared by every map on the page.
- **3D:** MapLibre GL, loaded with a dynamic `import()` the first time a viewer picks 3D, so the 2D bundle does not grow. Tilted view (pitch 55), OSM raster tiles, no token. Each point is an extruded column coloured by its band; clicking a column calls the same `onSelect`. Insured sites show as small circles.
- If WebGL or the chunk fails, the shell says so and keeps showing 2D.

Pure logic (mode persistence, band to colour and rank, GeoJSON columns) is in `map/shellLogic.ts` with tests in `shellLogic.test.ts`.

## What the 3D view does and does not show

- Column height is the band **order** (low, typical, elevated, peak; ok, near, over), never a measured value. The legend and the sentence next to the toggle say so.
- Colours stay amber for every model band, never red. Gauge "over MHW" uses the dark amber too.
- No terrain: a free elevation (DEM) tile source needs a key or a hosted tile service, so there is no relief. The view is pitch plus extruded markers. There are no river polylines because the views carry points only, not river geometry.

## 2D vs 3D trade-offs

| | 2D (Leaflet) | 3D (MapLibre GL) |
|---|---|---|
| Bundle | In the main chunk | Separate lazy chunk, about 1.1 MB (304 KB gzip) plus 72 KB CSS, fetched on first use |
| GPU | None needed (DOM / SVG) | WebGL required; heavier on old laptops and phones; falls back to 2D |
| Accessibility | Markers are focusable buttons with aria-label and titles; tooltips | Canvas: columns are not focusable and have no per-point aria-label. Use the point selector or the source list below the map |
| Keyboard | Tab to markers, Enter opens the popup; arrow keys pan and +/- zoom | Arrow keys pan, +/- zoom, Shift+arrows rotate and tilt; selecting a point needs the selector or list |
| Reading values | Colour dots | Column height (order only) plus colour; hover shows the label |
| Scroll behaviour | Wheel zoom off, page scrolls | Cooperative gestures: Ctrl + wheel to zoom |

Teammates can flip the toggle on any map to compare the two views on the same data.
