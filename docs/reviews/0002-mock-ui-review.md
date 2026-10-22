# 0002. Mock UI review

- Reviewed: `spike/mock-ui` at `58a86ab` (everything under `ui/`)
- Date: 2026-10-22
- Standard: the mock becomes the real UI if the team adopts it, so components read data only through `ui/src/api`, behind the types in `ui/src/types`.

## Verdict

At `58a86ab` the mock is not ready to call done. The shape the plan depends on is already there, and it should stay: components import data only from `src/api/client`, mocks stay behind that layer, and there is no `any`, no committed secret, and no shell-specific script. The OpenStreetMap default follows the tile usage policy (HTTPS, visible attribution, no prefetch, no `no-cache`).

What blocks "done" is labelling. A live PEGELONLINE measurement opens an evidence panel stamped "SAMPLE QUOTE", and the map footer credits PEGELONLINE for Valencia and for sample fallbacks. A reviewer, or the later swap from mock to real data, can treat invented numbers as the federal feed.

The fixes on this branch address that, plus the Medium items below and the small Lows that were only deletions. With those in place the mock is ready to call done. Still deferred, as already agreed: the Vite/esbuild dev-server audit, keyboard access to map markers, rectangle region bounds, and the proxy gauge colours.

## High

### Live measurements are labelled as sample quotes

`ui/src/components/citations/CitationPanel.tsx` (`CitationPanel`). The panel always rendered `MOCK CITATION · SAMPLE QUOTE`. Live gauges register a citation with `quoteIsSample: false` in `ui/src/api/gauges.ts` (`toLiveStation`), and the quote heading already hid the sample chip in that case. The badge ignored the flag. The header and the citizen view also said sample data for the whole screen, including the map that is live.

Why it matters: the evidence panel is where someone checks that sample text and live measurements are not mixed up. A real PEGELONLINE sentence labelled as a sample quote breaks the rule in `ui/README.md`, and it teaches the next swap to leave the badge in place after the numbers become real.

Fix: when `quoteIsSample` is false, show the Live badge and title the section "Measurement". Keep the sample badge for mock quotes. The shell and the citizen view say "MOCK UI", with a tooltip that figures are sample unless marked Live. The insurer view stays "MOCK DATA"; that view has no live feed.

Fixed on this branch.

## Medium

### The map footer always credits PEGELONLINE

`ui/src/components/map/GaugeMap.tsx` (`FeedFooter`) imported `pegelonlineConfig` and always printed the federal licence, including when `provenance` was `"sample"`. `ui/src/api/gauges.ts` (`sampleRegionGauges`) special-cased `regionId === "valencia"` and otherwise stored `"Sample values"`, but the footer never read `RegionGauges.attribution`. On a fully sample payload the footer also added a second Sample badge whose detail said "state-portal gauges", which is wrong for federal stand-ins and for Valencia.

Why it matters: Valencia and a failed fetch showed invented levels next to "© www.pegelonline.wsv.de" and "raw data, unchecked". That is the mix-up the licence note is there to prevent. The Valencia branch also meant a new region had to edit `gauges.ts`.

Fix: `Region.sampleAttribution` carries the sample credit, and the footer renders `gauges.attribution`. The PEGELONLINE sentence, licence URL, and the proxy-threshold caveat are built only for a live federal fetch. The extra Sample badge appears only when a live payload also contains sample stations. `client.ts` no longer re-exports the PEGELONLINE config; components do not need it.

Fixed on this branch.

### Every thrown error became "PEGELONLINE could not be reached"

`ui/src/api/gauges.ts` (`getRegionGauges`, `getGaugeObservations`) caught every error and showed sample levels. `ui/src/api/pegelonline.ts` (`getJson`) cast the body with `as T` and did not check that it was a list.

Why it matters: a mapper bug, such as a station with no `water` object or a JSON object where a list was expected, was described as a network failure and replaced with invented flood levels. Timeout and HTTP failures should still fall back. A programming error should not.

Fix: `PegelonlineError` is thrown only for timeout, network failure, a non-OK status, invalid JSON, or a body that is not a list. The gauge functions fall back only on that type and rethrow anything else. A station with no coordinates, no water, or no `"W"` series is skipped.

Fixed on this branch. A direct request for the Bavaria box returned HTTP 200, 57 stations inside the box, water-level unit `cm`.

### A second approval spends another agent call, and the simulation hides the failure

`ui/src/api/insurer.ts` (`decideApproval`) did not look at `status`. The queue and the alert simulation both call it, so a double click, or Approve in both places, consumed two rate-limit tokens and pushed two notifications. `ui/src/components/insurer/AlertSimulation.tsx` (`decide`) dropped the rejected promise, so a rate-limit error left the stepper on "Human decision". The queue path already shows `decisionError` in `InsurerView`.

Why it matters: the header budget is part of the demo. A repeated click makes that budget look wrong, and a failed simulation step looks like a hang.

Fix: one in-flight decision per request. If the request is no longer pending, return it and do not call `consumeRequest`. The simulation shows the error and disables Approve and Reject while the call is in flight.

Fixed on this branch.

### The replay timer updates state from inside a state updater

`ui/src/hooks/useReplayPlayer.ts`. At the last hour the interval called `setPlaying(false)` inside the `setHourState` updater. Updaters have to be pure. React Strict Mode runs them twice, and stopping playback is not a new hour. The interval was cleared when `playing` flipped or the component unmounted, so this was not a leaked timer.

Why it matters: the playhead and the `playing` flag can disagree, and the nested update is the sort of effect that starts warning under a stricter React.

Fix: when `hour` is the last hour, the effect sets `playing` to false. The updater only returns the next hour.

Fixed on this branch.

## Low

### Dead code, and a tile URL that was not checked

- `delay` in `ui/src/api/mockTransport.ts` had no callers. Removed.
- `Region.zoom` was never read. `LeafletMap` fits `bounds` and sets `zoomSnap: 1`. Removed, so a new region is not given a field the map ignores. The comment on `BoundingBox` said it was lat/lon pairs; the fields are `south`, `west`, `north`, and `east`. Corrected.
- `.sr-only` and `.visually-hidden` in `ui/src/styles/global.css` were the same rule. The replay label uses `visually-hidden`.
- `ui/src/api/config.ts` (`mapTiles`) used `??`, so a blank string or an `http://` URL would have been passed to Leaflet. The committed default is the HTTPS OpenStreetMap endpoint with attribution, so the demo as committed was fine. A custom URL now has to be `https://` and has to bring its own attribution, or the map stays on OpenStreetMap and warns. While the tiles are OpenStreetMap's, their credit is kept even if `VITE_MAP_ATTRIBUTION` is set. The "Report a map issue" link is added only for OpenStreetMap, whose policy asks for it.

Fixed on this branch. These were deletions or a guard around config the demo does not set.

### Left as they are

- `useAsync` takes its dependency list as an argument, the same contract as `useEffect`. Callers pass the ids the loader closes over. A smarter wrapper would be another abstraction the mock does not use.
- `TtlCache`, `createStore`, and the rate limiter each back something on screen: one PEGELONLINE request per region (Strict Mode would otherwise fire two), the shared approval and notification state, and the header budget. The answer cache stays separate because a hit must keep the original timestamp and must not consume a call.
- The nearby gauge list (`getGauges`) and the map (`getRegionGauges`) are different contracts. The card is sample data from the state-portal mocks; the map is the live feed. Merging them would hide that.
- `getGaugeForecast` rejects when `levelCm` is null. `useAsync` catches it and the chart omits the band.
- The rate-limit subscription starts one interval per subscriber. Only the header subscribes, and unsubscribe clears the interval.
- `knownStations` remembers stations for the life of the page so drill-down can resolve an id. That matches `getGaugeObservations(stationId)` and is gone on reload.
- The citation drawer moves focus to Close and closes on Escape. It does not trap focus. Enough for the mock.
- Keyboard access to markers, proxy colours, rectangle bounds, and the Vite/esbuild audit stay deferred.

## Checked, no finding

- Direction of dependencies: under `src/components`, data imports are only from `src/api/client`. Nothing there imports `src/mocks`.
- TypeScript is `strict` with `noUnusedLocals`. No `any`, no `ts-ignore`.
- Secrets: `.env` and `.env.*` are ignored at the repo root and in `ui/.gitignore`, with `!.env.example` kept. The example file has public URLs only. No token in the UI tree.
- Windows: the `package.json` scripts are `vite` and `tsc`, joined with `&&`. npm runs that through `cmd.exe` on Windows. There is no bash and no hardcoded separator. `node scripts/gen-citations.mjs` uses `node:` built-ins and `import.meta.url`.
- OpenStreetMap: the default tile URL is `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. The built-in attribution control is replaced by a visible one, not removed. `scrollWheelZoom` is off, `zoomSnap` is 1, and the tile layer sets no cache-busting header and no `Referrer-Policy`. Attribution links use `rel="noopener"` and not `noreferrer`, so the browser still sends its default `Referer` on tile requests. `rel="noreferrer"` on citation links does not apply to tiles.
- PEGELONLINE: HTTPS, 10 second abort, 5 minute cache with in-flight de-duplication, sample fallback with a reason, Live and Sample badges, dashed markers for sample stations.
- Leaflet, the splash timeout, the ask-panel stages, and the simulation steps clear their timers or call `map.remove()` on cleanup. Hash, theme, and dismiss listeners unsubscribe.

## Over-engineering

Nothing structural needs to come out. One module per data need, re-exported from `client.ts`, is the seam that lets a mock function be replaced without editing a component. Collapsing it would save files and cost that plan. The deletions in this review are the pieces that were not pulling their weight: `delay`, `Region.zoom`, the duplicate screen-reader class, and the footer reaching past the data contract into PEGELONLINE config.
