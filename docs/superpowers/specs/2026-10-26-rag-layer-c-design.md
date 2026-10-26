# RAG layer (c) — tool RAG

Status: design, locked by Mihir on 26 Oct 2026. `v0.14.0` is the layer (c) ship tag and is not cut in this document. `v0.11.0` is the retired name and is not a tag.

This document does not ingest a corpus, add a tool, or change the agent runtime. That work is the next pull request. `v0.13.0` is the demo baseline already tagged on main. This design does not cut `v0.13.0`, `v0.14.0`, or any other tag.

`FF_RAG_DOCS` stays off. With the flag off, or when retrieval returns nothing, the run is today's SQL-only path: layers (a) and (b) through Zetaris.

## Approaches

| Approach | What it does | Decision |
| --- | --- | --- |
| A. Classic always-on RAG | Every question retrieves passages and stuffs them into the prompt | Rejected. The demo's numbers still come from SQL, and a silent retrieve would cite documents the Investigator did not ask for |
| B. Tool RAG | The Investigator calls `retrieve_docs(query, k, filters)` when it wants a document passage | Chosen |
| C. Agentic multi-hop | The model plans several retrieves, rewrites the query, and walks the corpus | Out of `v0.14.0` |

One retrieve per call. No query rewrite, no second hop, no reranker.

## What ships in v0.14.0

- A git corpus of redistributable documents, with a manifest.
- Hierarchical chunks and 2048-dimension embeddings in pgvector (`docker compose --profile rag`, host port `127.0.0.1:15432`).
- Approximate nearest neighbour search with `<=>` inside that Postgres only.
- Hydration of text, licence, and locator through Zetaris JDBC, so the citation carries a `query_id`.
- The Investigator may call `retrieve_docs` only when `FF_RAG_DOCS` is on.
- A layer (c) citation whose quote hashes to `content_sha256`.

## What does not ship in v0.14.0

- Agentic multi-hop retrieval.
- A reranker.
- BM25 or any hybrid lexical index.
- A news wire, or any paywalled article.
- H-MEM or the World Model as the document store.

## Corpus

The corpus is Tier 1 + Tier 2 + Tier 3. Tier 1 and Tier 2 are the sets previously called A and B. The path is `corpus/` at the repo root (not `data/rag-corpus/`).

| Tier | Documents | Licence we rely on | Attribution we store |
| --- | --- | --- | --- |
| 1 | Copernicus EMSR773 (Valencia, activation 2024) — https://mapping.emergency.copernicus.eu/activations/EMSR773 | CEMS On-Demand Mapping terms: free, full, and open access to reproduce, distribute, and communicate. Recorded in `docs/legal/sources.md` | `Copernicus Emergency Management Service (© 2024 European Union), EMSR773` |
| 1 | Copernicus EMSR517 (Ahr / western Germany, activation 2021) — https://mapping.emergency.copernicus.eu/activations/EMSR517 | Same CEMS terms. Activation year 2021 | `Copernicus Emergency Management Service (© 2021 European Union), EMSR517` |
| 2 | HESS Valencia personal weather stations. Rombeek, Hrachowitz, and Uijlenhoet, Hydrol. Earth Syst. Sci., 29, 6715–6733, 2025. https://doi.org/10.5194/hess-29-6715-2025 — PDF https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf | CC BY 4.0 | `Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0, https://doi.org/10.5194/hess-29-6715-2025` |
| 2 | NHESS July 2021 flood, Part 2. Ludwig, Mohr, and co-authors, Nat. Hazards Earth Syst. Sci., 23, 1287–1311, 2023. https://doi.org/10.5194/nhess-23-1287-2023 — PDF https://nhess.copernicus.org/articles/23/1287/2023/nhess-23-1287-2023.pdf | CC BY 4.0 | `Ludwig, Mohr, and co-authors (2023), CC BY 4.0, https://doi.org/10.5194/nhess-23-1287-2023` |
| 2 | EasyxLab S19, "What the maps did not show" (Valencia DANA dwellings and official flood maps). Text and published aggregates: https://easybyte.es/lab/studies/s19/paper/ | CC BY 4.0 for EasyxLab's own text and data. Code on that study is Apache-2.0 and is not part of the corpus | `EasyxLab (2026), Study S19, CC BY 4.0, https://easybyte.es/lab/studies/s19/paper/` |
| 3 | Open official RSS feeds and situation bulletins whose licence allows storing the full text | Same gate as tiers 1 and 2. A bulletin is added only after `docs/legal/sources.md` records the licence, the attribution string, and that full text may be stored | The string that page records |

The first manifest may contain zero Tier 3 files. Tier 3 is an admission rule, not a promise that a feed is already chosen.

Excluded, and not fetched:

- Paywalled news and news wires. Pointer-only quotes of the press stay a layer (b) concern. They are not in this corpus.
- Generalitat Valenciana / Institut Cartogràfic Valencià, "Zona inundada por la DANA del 29 de octubre de 2024", CC BY-NC-ND 4.0. EasyxLab S19 counts against that layer and does not republish the geometry. We store S19's CC BY text. We do not store the Generalitat geometry or any derived geometry.
- Any text under CC BY-NC, CC BY-ND, CC BY-NC-ND, or a terms page that forbids storing a copy.

### Layout

```text
corpus/manifest.yaml       # tracked
corpus/pdf/                # tracked redistributable PDFs and bulletin snapshots
corpus/fetched/            # gitignored. Oversized files downloaded by the task
corpus/.embed-cache/      # gitignored. Embedding vectors, not the documents
```

`corpus/manifest.yaml` is a list. Every entry has these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `doc_id` | yes | Stable id, used as the first segment of `path` on each chunk |
| `title` | yes | Citation title |
| `publisher` | yes | Citation publisher |
| `url` | yes | `https` page or file the copy came from |
| `licence` | yes | SPDX id or the CEMS terms name |
| `attribution` | yes | The string the UI shows |
| `sha256` | yes | Lower-case SHA-256 hex of the file bytes |
| `tier` | yes | `1`, `2`, or `3` |
| `event_id` | tiers 1 and 2 | `EMSR773` or `EMSR517`. Tier 3 may set it when the bulletin is about one activation, or leave it null |
| `path` | yes | Path relative to `corpus/` |
| `placement` | yes | `git` or `fetch` |

`placement: git` means the file is committed under `corpus/pdf/`. `placement: fetch` means the file is larger than GitHub's 100 MiB limit, or is a CEMS product zip we do not want in git. `python tasks.py fetch-rag-corpus` downloads those entries into `corpus/fetched/`, checks `sha256`, and does not embed them. The task is specified here and written in the next pull request. It does not start compose and it does not call the embedding API.

Git tracks the manifest and the redistributable PDFs. Git ignores only:

- the pgvector data volume (`floodsense-app_pgdata` in `compose.yaml`, which is a Docker volume, not a path in the tree)
- `corpus/.embed-cache/`
- `corpus/fetched/`

`compose.yaml` already publishes pgvector on `127.0.0.1:15432` under profile `rag`. This design does not change that file.

## Store

Postgres in the `rag` profile holds the chunks. The image is the existing `pgvector/pgvector:pg16` service. ADR 0009 measured pgvector 0.8.7 there.

One table, `rag.chunks`. Retrieval rows are paragraphs. Document, page, and section rows exist so a paragraph has a parent.

| Column | Notes |
| --- | --- |
| `chunk_id` | Primary key. This is the optional citation `chunk_id` |
| `parent_chunk_id` | Null on the document row. A page or section points at the document. A paragraph points at its page or section |
| `path` | `doc_id`, then `p{page}` or `s{section}`, then `para{n}`. Example: `hess-29-6715-2025/p12/para3` |
| `level` | `doc`, `page`, `section`, or `paragraph` |
| `doc_id`, `tier`, `event_id` | Copied from the manifest |
| `title`, `source_url`, `publisher`, `licence`, `attribution` | Copied from the manifest onto every row of that document, so hydration does not join a second table |
| `page`, `paragraph`, `lines`, `section` | Locator copied onto a layer (c) citation. Every paragraph that can be cited sets `page` ≥ 1, `paragraph` ≥ 1, and `lines`. `section` may also be set, and it may be null. It does not replace `page` |
| `text` | The passage. Paragraph rows hold the paragraph. Parent rows may hold a heading |
| `text_sha256` | SHA-256 hex of `text` as UTF-8. This is the chunk hash. It is not the citation `content_sha256` |
| `embedding` | `vector(2048)`, null except on `level = paragraph` |
| `embed_model` | `nvidia/llama-nemotron-embed-1b-v2` when `embedding` is set |

Chunks follow the document's structure (document, then page or section, then paragraph). They are not fixed-size windows. A paragraph longer than the model's 8192-token limit is split on line boundaries into sibling paragraphs under the same parent, and `lines` records the range inside the original paragraph (`3-5`).

Every paragraph that can be cited as layer (c) sets `page` ≥ 1, `paragraph` ≥ 1, and `lines`. `page` is never null. When the source has no PDF pagination (section-structured text, EasyxLab S19, Tier 3 bulletins), ingest still assigns a page-like id: `1` for the whole document, or one id per section. A section-only row is not left uncitable only because it has no PDF page number. `section` stays optional and does not stand in for `page`. The path may still use `s{section}` for a section parent.

### ANN

The distance operator is pgvector cosine distance, `<=>`. It runs in this Postgres and nowhere else. Zetaris reads `<=>` as null-safe equality (ADR 0009). Agents never send `<=>` or `<->` in Zetaris SQL.

The column is `vector(2048)`. pgvector will not build an HNSW or IVFFlat index on a `vector` wider than 2000 dimensions. The ANN index is therefore half-precision, which indexes up to 4000 dimensions:

```sql
CREATE INDEX rag_chunks_embed_hnsw
  ON rag.chunks
  USING hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)
  WHERE level = 'paragraph' AND embedding IS NOT NULL;
```

The search uses the same expression, so the planner can use the index:

```sql
SELECT chunk_id, (embedding::halfvec(2048) <=> $1::halfvec(2048)) AS distance
FROM rag.chunks
WHERE level = 'paragraph'
  AND embedding IS NOT NULL
  AND ($2::text IS NULL OR event_id = $2)
ORDER BY embedding::halfvec(2048) <=> $1::halfvec(2048)
LIMIT $3;
```

`$1` is the query embedding cast to `halfvec(2048)`. The stored column stays full `vector(2048)`. The cast is the index expression, not a second model and not a reranker. The dimension stays 2048. We do not truncate the model output to 2000 to fit a `vector` index. `v0.14.0` ships that index and that query. If the installed pgvector refuses the halfvec index, the fallback is an exact `ORDER BY embedding <=> $1::vector` with no ANN index. The operator stays `<=>` in Postgres either way.

### Embeddings

| Item | Value |
| --- | --- |
| Model | `nvidia/llama-nemotron-embed-1b-v2` |
| Endpoint | `POST https://integrate.api.nvidia.com/v1/embeddings` (`NIM_EMBEDDINGS_URL` may replace that URL for a local NIM) |
| Dimension | 2048 (`dimensions: 2048` on every request; no smaller Matryoshka size) |
| Passage ingest | `input_type: "passage"` |
| Query | `input_type: "query"` |
| Auth | `Authorization: Bearer` from `NVIDIA_NIM_API_KEY` |

The body is `{"model","input","input_type","dimensions"}`. `input` is a list of strings. This model requires `input_type`. Passage vectors and query vectors are not interchangeable.

Nightshift does not serve embeddings. Runtime 1.4 has no `/v1/embeddings` we can depend on, and `scripts/nightshift_check.py` treats `POST /embeddings` as an optional probe. Layer (c) does not call that probe and does not send the document model through a chat lane. Chat completions stay on Nightshift (`meterless/fast`, `meterless/deep`) under ADR 0004. The NIM call is the embedding exception that ADR 0009 records: ingest and `retrieve_docs` only.

`NVIDIA_NIM_API_KEY` lives in the gitignored `agents/.env` (and in the environment of the ingest command). It is not committed, not logged, not a fixture, and not a Nightshift Providers-tab key. The NVIDIA chat key stays in Nightshift's Providers tab.

The embedding cache is `corpus/.embed-cache/nvidia/llama-nemotron-embed-1b-v2/2048/{passage|query}/{sha256}.json`, where `{sha256}` is the SHA-256 of the UTF-8 text that was embedded. A cache hit skips NIM. The cache is not the corpus and is not pgvector.

### What H-MEM and the World Model are

H-MEM and the World Model stay claim and hypothesis memory. The H-MEM reference embedder (`engines/vendor/hmem/reference/src/embeddings.ts`) is a 64-dimension FNV-1a hash stub. `v0.9.0` recalls approved claims with it when `FF_HMEM` is on. That stub is not the document embedder, the chunk table is not written to the sidecar, and `v0.14.0` does not replace the vendor hash. The World Model board is unchanged.

## Online path

`FF_RAG_DOCS` defaults off (`agents/.env.example`, `settings.ff_rag_docs`). Off means `retrieve_docs` is not registered. The Investigator's SQL tools are the whole data path. No NIM call, no pgvector call.

On means the Investigator may call the tool. It is not called for the Investigator on every turn. Watchers, Exposure, the Skeptic's counter-checks, and the Judge do not call it.

```text
retrieve_docs(query: string, k: integer, filters: { event_id?: "EMSR773" | "EMSR517" })
```

`k` is from 1 to 20. The Investigator passes the run's `event_id` in `filters`. Omitting `event_id` searches every paragraph in the corpus; the Investigator does not omit it.

Steps, in order:

1. Embed `query` with `input_type: "query"` and `dimensions: 2048`. Read the cache first.
2. Run the ANN statement in pgvector. Keep `chunk_id` and `distance`. This statement does not go through Zetaris.
3. Hydrate those ids through Zetaris JDBC. The statement selects `text`, `text_sha256`, `title`, `source_url`, `publisher`, `licence`, `attribution`, `page`, `paragraph`, `lines`, and `section`. It does not select `embedding` and it does not contain `<=>`. The Zetaris response supplies `query_id`.
4. Build one layer (c) citation per hydrated row. If hydrate fails, or returns fewer rows than the id list, drop the missing ids. Do not cite a chunk that has no `query_id`. Do not drop a paragraph only because the source has no PDF page; ingest has already set `page` ≥ 1.
5. An empty id list returns an empty list. The Investigator adds no layer (c) citation. The SQL claims stand on their own.

`distance` is cosine distance (lower is nearer). The citation record does not carry the distance. Order of the tool result is the ANN order.

The quote is a verbatim slice of `text`. If `text` is at most 600 characters, the quote is `text` and `lines` is that paragraph's line span (`1-1` when the paragraph is a single line). If it is longer, the quote is a verbatim line range inside that paragraph, still at most 600 characters, and `lines` names that range. `content_sha256` is the lower-case SHA-256 hex of the quote as UTF-8. The quote is a substring of the chunk `text`, and `text_sha256` on the row is the hash of that full `text`. The citation field stays the quote hash, which is what the Judge already compares.

`storage` is `full_text` for every document in this corpus. Pointer storage is for sources we do not keep, and those sources are not in the corpus.

### Layer (c) citation

Required on layer `c`, in addition to the fields every citation already requires (`citation_id`, `claim_id`, `layer`, `source_url`, `title`, `publisher`, `accessed_at`, `licence`, `attribution`, `content_sha256`, `storage`):

| Field | Rule |
| --- | --- |
| `quote` | Verbatim. One or two sentences, at most 600 characters |
| `locator.page` | Integer ≥ 1 on every citable paragraph. Never null. A source with no PDF pagination still sets a page-like id (`1` for the whole document, or one id per section). `section` does not replace `page` |
| `locator.paragraph` | Integer ≥ 1 |
| `locator.lines` | Non-empty, for example `3-5` |
| `query_id` | The Zetaris id from the hydrate |
| `content_sha256` | `sha256(quote)` as UTF-8 |

`locator.section` stays optional. It does not stand in for `locator.page`. The page rule above is the only rule for whether a paragraph can be cited. `chunk_id` stays optional on the wire so a citation that names the passage without the store id still validates. The tool sets `chunk_id` from the row when it has one.

Layers `a` and `b` do not require `quote`, `locator`, `query_id`, or `chunk_id`. A layer (a) or (b) citation that omits them stays valid. The schema rule is `if layer = c`.

### Judge

`agents/floodsense_agents/nodes/judge.py` seeds `citation_faithful` from layer (a) evidence. At least one layer (a) citation has a `query_id` present in that evidence, and every such evidence row has `row_count > 0` and no error. The same function then ANDs the quote hash for each layer (c) citation that carries both `quote` and `content_sha256`: `sha256(quote)` as UTF-8 equals `content_sha256`. A layer (c) citation on its own does not pass. This design does not change that function. The substring check of the quote against the chunk `text`, and the comparison of that passage to `text_sha256`, stay the next pull request. The Judge still does not approve the claim.

## Flag off and empty retrieve

Both leave the graph on the SQL path that ships today.

- Flag off: the tool is absent. The Investigator cannot call it. No layer (c) citation is produced by retrieval.
- Flag on, empty list: the tool returns `[]`. No layer (c) citation is attached. Claims that already have layer (a) or (b) citations are unchanged.

A failed NIM call or a failed pgvector call is a tool error on the trace. It does not invent a passage and it does not fail the run. The SQL path still completes.

## This pull request and the next

This pull request:

- This spec.
- The layer (c) rule and optional `chunk_id` on the citation contract, with the Python and TypeScript mirrors and an example. Layers (a) and (b) stay valid without those fields.
- ADR 0009 records the embedding model and closes the metadata-hop question.
- The gameplan names `v0.14.0` as the layer (c) ship tag.
- A changelog line under `## [Unreleased]`.
- Gitignore entries for `corpus/.embed-cache/` and `corpus/fetched/`.

The next pull request (not this one):

- `corpus/manifest.yaml` and the redistributable PDFs.
- `python tasks.py fetch-rag-corpus`.
- The `rag.chunks` migration and the Zetaris JDBC registration (`PGVECTOR_PASSWORD` stays a `${VAR}` placeholder, as ADR 0009 already says).
- The NIM client, the ingest, and `retrieve_docs` behind `FF_RAG_DOCS`.
- The Investigator call and the substring check in the Judge.

No runtime RAG code lands in this pull request.
