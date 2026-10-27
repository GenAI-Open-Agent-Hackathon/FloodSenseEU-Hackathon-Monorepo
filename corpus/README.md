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
| `eea-briefing-economic-losses-2025` | `pdf/eea-briefing-economic-losses-2025.html` | EEA briefing (2025), CC BY 4.0. Losses and the insurance protection gap, EEA-38, 1980-2023. Scripts, styles and links removed. Tier 3, audience insurer |
| `eea-briefing-economic-losses-2022` | `pdf/eea-briefing-economic-losses-2022.html` | EEA briefing (2022), CC BY 4.0. Insured share of losses, EEA-32, 1980-2020. Scripts, styles and links removed. Tier 3, audience insurer |
| `eiopa-19-485` | `pdf/eiopa-19-485-protection-gap.pdf` | EIOPA Staff Discussion Paper on the natural catastrophe protection gap (2019), reproduction authorised by the EIOPA legal notice. Tier 3, audience insurer |
| `eu-floods-directive-2007-60-ec` | `pdf/eu-floods-directive-2007-60-ec.pdf` | Directive 2007/60/EC, original OJ text, Commission reuse policy. Tier 3, audience authority |

Tier 3 is an admission rule. Tier 3 files are `boe-a-2004-18910` and the four event-agnostic insurer and authority documents above (`event_id: null`). Retrieval inside an event run also returns `event_id: null` rows. A bulletin is added only after `docs/legal/sources.md` records the licence, the attribution, and that full text may be stored.

```bash
python tasks.py fetch-rag-corpus
```

The command checks every `placement: git` sha256. It downloads `placement: fetch` entries into `corpus/fetched/` (gitignored) and checks those sha256 values. `corpus/.embed-cache/` is gitignored. The command does not start Docker and does not call an embedding API.

Each entry may carry `audience` (insurer, citizen, authority), `language` and `year`. They are manifest metadata only: `rag.chunks` has no audience column, so retrieval does not filter on it yet.

Licences and the attribution strings are in `docs/legal/sources.md`.
