# Corpus

Layer (c) documents, shipped in `v0.14.0`. `FF_RAG_DOCS` stays off. This folder does not embed and it does not create `rag.chunks`. `scripts/rag_ingest.py` does that.

`corpus/manifest.yaml` is the list. Each file below it is a redistributable copy:

| doc_id | File | Why this copy |
| --- | --- | --- |
| `emsr773-aoi03-del` | `pdf/emsr773-aoi03-delineation-map.pdf` | Horta Sud (AOI03) delineation map, taken out of product zip `EMSR773_AOI03_DEL_PRODUCT_v1.zip`. The zip and its shapefiles are not stored |
| `emsr517-aoi15-gra` | `pdf/emsr517-aoi15-grading-map.pdf` | Bad Neuenahr-Ahrweiler (AOI15) grading map |
| `hess-29-6715-2025` | `pdf/hess-29-6715-2025.pdf` | Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0 |
| `nhess-23-1287-2023` | `pdf/nhess-23-1287-2023.pdf` | Ludwig, Mohr, and co-authors (2023), CC BY 4.0 |
| `easyxlab-s19` | `pdf/easyxlab-s19.html` | EasyxLab S19 paper text. The Cloudflare scripts after the footer are not stored. The study's code is Apache-2.0 and is not in this folder. The Generalitat flood geometry is not in this file |
| `nhess-23-525-2023` | `pdf/nhess-23-525-2023.pdf` | Mohr and co-authors (2023), CC BY 4.0. July 2021 event analysis (10 MB) |
| `nhess-23-973-2023` | `pdf/nhess-23-973-2023.pdf` | Thieken and co-authors (2023), CC BY 4.0. German flood warning system in July 2021 |
| `boe-a-2004-18910` | `pdf/boe-a-2004-18910-original.pdf` | RDL 7/2004, Consorcio de Compensacion de Seguros statute, original 2004 BOE text under the BOE reuse conditions. Tier 3. Not the consolidated text |
| `eea-briefing-economic-losses-2025` | `pdf/eea-briefing-economic-losses-2025.html` | EEA briefing (2025), CC BY 4.0. Losses and the insurance protection gap, EEA-38, 1980-2023. `<script>`, `<style>` and `<link>` tags removed. Tier 3, audience insurer |
| `eea-briefing-economic-losses-2022` | `pdf/eea-briefing-economic-losses-2022.html` | EEA briefing (2022), CC BY 4.0. Insured share of losses, EEA-32, 1980-2020. `<script>`, `<style>` and `<link>` tags removed. Tier 3, audience insurer |
| `eiopa-19-485` | `pdf/eiopa-19-485-protection-gap.pdf` | EIOPA Staff Discussion Paper on the natural catastrophe protection gap (2019), reproduction authorised by the EIOPA legal notice. Tier 3, audience insurer |
| `eu-floods-directive-2007-60-ec` | `pdf/eu-floods-directive-2007-60-ec.pdf` | Directive 2007/60/EC, original OJ text, Commission reuse policy. Tier 3, audience authority |
| `wiki-1997-central-european-flood` | `pdf/wiki-1997-central-european-flood.html` | Wikipedia "1997 Central European flood", revision 1368946079, CC BY-SA 4.0. Oder (and Morava), July 1997. Tier 3, country EU, audience citizen |
| `wiki-2002-european-floods` | `pdf/wiki-2002-european-floods.html` | Wikipedia "2002 European floods", revision 1374296101, CC BY-SA 4.0. Elbe at Dresden, Vltava at Prague, Danube, August 2002. Tier 3, country EU, audience citizen |
| `wiki-2010-central-european-floods` | `pdf/wiki-2010-central-european-floods.html` | Wikipedia "2010 Central European floods", revision 1359816549, CC BY-SA 4.0. Vistula and Oder, May-June 2010. Tier 3, country PL, audience citizen |
| `wiki-2013-european-floods` | `pdf/wiki-2013-european-floods.html` | Wikipedia "2013 European floods", revision 1372735297, CC BY-SA 4.0. Elbe (Magdeburg), Danube (Passau), Vltava, Rhine/Main/Neckar shipping, June 2013. Tier 3, country EU, audience citizen |
| `wiki-2016-european-floods` | `pdf/wiki-2016-european-floods.html` | Wikipedia "2016 European floods", revision 1360455033, CC BY-SA 4.0. Neckar region, Rhine near Bonn, Seine, Loiret, May-June 2016. Tier 3, country EU, audience citizen |
| `wiki-2021-european-floods` | `pdf/wiki-2021-european-floods.html` | Wikipedia "2021 European floods", revision 1375935659, CC BY-SA 4.0. Ahr, Erft, Meuse at Liege and Venlo, Kyll near Trier, July 2021. Tier 3, country EU, audience citizen |
| `wiki-2024-central-european-floods` | `pdf/wiki-2024-central-european-floods.html` | Wikipedia "2024 Central European floods", revision 1377676053, CC BY-SA 4.0. Storm Boris: Danube at Vienna and Budapest, Oder basin, Czechia, September 2024. Tier 3, country EU, audience citizen |
| `wiki-2024-spanish-floods` | `pdf/wiki-2024-spanish-floods.html` | Wikipedia "2024 Spanish floods", revision 1379732613, CC BY-SA 4.0. Valencia DANA, Barranc del Poyo, Paiporta, 29 October 2024. Tier 3, country ES, audience citizen |
| `wiki-seine` | `pdf/wiki-seine.html` | Wikipedia "Seine", revision 1381786474, CC BY-SA 4.0. Seine at Paris: 1910, 2016, 2018 (section Dams and flood control). Tier 3, country FR, audience citizen |
| `wiki-moselle` | `pdf/wiki-moselle.html` | Wikipedia "Moselle", revision 1374522670, CC BY-SA 4.0. Mosel at the Trier gauge: 1983, 1993, 1995, 1997 high water. Tier 3, country EU, audience citizen |
| `wiki-neckar` | `pdf/wiki-neckar.html` | Wikipedia "Neckar", revision 1381972636, CC BY-SA 4.0. Neckar: October 1824 (HQ4000), February 1970. Tier 3, country DE, audience citizen |
| `wiki-flood-control-netherlands` | `pdf/wiki-flood-control-netherlands.html` | Wikipedia "Flood control in the Netherlands", revision 1369449074, CC BY-SA 4.0. Lower Rhine and Meuse, 1993 and 1995 flood threats. Tier 3, country EU, audience citizen |
| `wiki-list-of-floods` | `pdf/wiki-list-of-floods.html` | Wikipedia "List of floods", revision 1380945599, CC BY-SA 4.0. St. Mary Magdalene's flood (Rhine, Moselle, Main, Weser, Elbe, Danube), Seine 1910, Po 1951/1994/2001. Tier 3, country EU, audience citizen |

Tier 3 is an admission rule. Tier 3 files are `boe-a-2004-18910` and the four event-agnostic insurer and authority documents above (`event_id: null`). Inside an event run, retrieval keeps the event top k and appends at most 2 `event_id: null` passages, only for an insurer role or an insurance-type question, and only from `country` EU or the event's country (ES for EMSR773, DE for EMSR517). `rag.chunks` has no country column: the allowed doc_ids come from `agents/floodsense_agents/rag_scope.json`, written from this manifest by `python scripts/rag_corpus.py --write-scope` and checked by a test. A bulletin is added only after `docs/legal/sources.md` records the licence, the attribution, and that full text may be stored.

```bash
python tasks.py fetch-rag-corpus
```

The command checks every `placement: git` sha256. It downloads `placement: fetch` entries into `corpus/fetched/` (gitignored) and checks those sha256 values. `corpus/.embed-cache/` is gitignored. The command does not start Docker and does not call an embedding API.

Each entry may carry `audience` (insurer, citizen, authority), `language`, `year` and `country`. `rag.chunks` has none of these columns; retrieval does not filter on audience.

Licences and the attribution strings are in `docs/legal/sources.md`.

River history (`wiki-*`, 27 Oct 2026). Thirteen English Wikipedia snapshots on past floods of the watched rivers and their weather triggers (Genoa lows, Storm Boris, stalled cut-off lows, DANA). Each file is the paragraph text of one pinned revision (`oldid` in the URL) with a licence and attribution header as its first paragraph; tables, infoboxes and reference markers are removed. CC BY-SA 4.0: the files stay under that licence. They are `event_id: null` with a country, so `rag_scope.json` lists them. A Europe live watch run (event `LIVE-EU`) reads only these event-agnostic documents: all of them, or EU plus one country when the filters carry `country`. The demo seed (`api/app/demo_seed.py`, `HISTORY`) stores about five findings per river that cite them by doc_id, section (`page`) and paragraph; `api/tests/test_demo_seed_history.py` checks each number against the cited paragraph. Evals: `evals/river_history.yaml`.

Ingest (writes `rag.chunks`; needs `PGVECTOR_DSN` and `NVIDIA_NIM_API_KEY` in the environment; it replaces each doc_id's rows and embeds every manifest document again):

```bash
python tasks.py fetch-rag-corpus
python scripts/rag_ingest.py
```
