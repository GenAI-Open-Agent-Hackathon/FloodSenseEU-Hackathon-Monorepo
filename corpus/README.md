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

Tier 3 is an admission rule. The manifest has no Tier 3 file. A bulletin is added only after `docs/legal/sources.md` records the licence, the attribution, and that full text may be stored.

```bash
python tasks.py fetch-rag-corpus
```

The command checks every `placement: git` sha256. It downloads `placement: fetch` entries into `corpus/fetched/` (gitignored) and checks those sha256 values. `corpus/.embed-cache/` is gitignored. The command does not start Docker and does not call an embedding API.

Licences and the attribution strings are in `docs/legal/sources.md`.
