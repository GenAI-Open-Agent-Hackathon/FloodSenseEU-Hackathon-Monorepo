# Evaluation set: source list (Valencia, Oct 2024)

Draft list for `evals/`. Scope is the five-source plan, so this covers Valencia 2024 only. The Ahr / NRW July 2021 event comes back with the deferred German sources.

Each eval item needs a question, the facts a good answer contains, the allowed sources below, a reference answer with citations, and human labels per claim. Target: at least 10 items.

| Source | Use in the eval | Layer | Licence | Status |
| --- | --- | --- | --- | --- |
| Copernicus EMS EMSR773 delineation and grading layers | Flood extent, flooded hectares per AOI, sites inside the footprint | (a) + (b) | Copernicus EMS terms | Staged in `ems_footprint.csv`. Licence to confirm |
| Copernicus EMSR773 activation record (reason, event and activation time) | Event timeline: rain event 2024-10-29 14:30 UTC, activation 16:40 UTC | (b) | Copernicus EMS terms | Fetched from the public API |
| Open-Meteo Flood (GloFAS) and rain archive | Discharge and rainfall before the event | (a) + (b) | CC BY 4.0 | Urvashi loads |
| AEMET observations and alert history | Rain totals, alert timeline | (b) | AEMET reuse terms | Not staged |
| OSM sites and the synthetic portfolio | Exposure questions ("which insured sites were flooded") | (a) | ODbL / generated | Staged in `osm_sites.csv`, `portfolio_synthetic.csv` |
| News coverage of the alert timeline | Pointer plus 1-2 sentence quote only | (b) | Copyrighted. Pointer-only | Not chosen yet |

## Candidate question types
1. Which municipality had the largest flooded area in AOI03, and how many hectares?
2. How many synthetic policies with flood cover sit inside the observed footprint, and what is their total sum insured?
3. When did the extraordinary rainfall start, and when was the activation requested?
4. Which schools or health sites fall inside the flood footprint?
5. How did discharge at the nearest GloFAS point compare with the previous year's peak?
