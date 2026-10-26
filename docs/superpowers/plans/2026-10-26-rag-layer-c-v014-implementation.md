# RAG layer (c) v0.14.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship tool RAG for citation layer (c) as four pull requests that end with `retrieve_docs` behind `FF_RAG_DOCS`, without cutting the `v0.14.0` tag and without turning that flag on.

**Architecture:** A git corpus of redistributable documents is chunked into a hierarchy (document, page or section, paragraph) and embedded at 2048 dimensions into `rag.chunks` in the compose `rag` Postgres. Ranking uses cosine distance `<=>` in that Postgres only. Text, licence, and locator are read back through a Zetaris JDBC registration so every layer (c) citation keeps a `query_id`. The Investigator may call `retrieve_docs` only when `FF_RAG_DOCS` is on. One call, no rewrite, no second hop, no reranker.

**Tech Stack:** Python 3.12 stdlib for `tasks.py` and `scripts/rag_corpus.py`. Postgres 16 with pgvector 0.8.7 (`pgvector/pgvector:pg16`, host `127.0.0.1:15432`). Zetaris Lightning SQL via `scripts/zetaris_sync.py`. NVIDIA NIM embeddings `nvidia/llama-nemotron-embed-1b-v2` over HTTPS. Agents stay on LangGraph. Chat stays on Nightshift.

## Global Constraints

- `FF_RAG_DOCS` stays off. With the flag off, or when retrieval returns nothing, the run is today's SQL-only path: layers (a) and (b) through Zetaris.
- `v0.14.0` is the layer (c) ship tag and is not cut in any of these pull requests. `v0.11.0` is the retired name and is not a tag. `v0.13.0` is the demo baseline already tagged on main.
- One retrieve per call. No query rewrite, no second hop, no reranker.
- No BM25 or any hybrid lexical index. No news wire. No paywalled article. No text under CC BY-NC, CC BY-ND, or CC BY-NC-ND. No Generalitat Valenciana / Institut Cartogràfic Valencià DANA geometry.
- Model `nvidia/llama-nemotron-embed-1b-v2`. Endpoint `POST https://integrate.api.nvidia.com/v1/embeddings`. `NIM_EMBEDDINGS_URL` may replace that URL. Dimension 2048 on every request (`dimensions: 2048`). Passage ingest uses `input_type: "passage"`. Query uses `input_type: "query"`.
- Auth is `Authorization: Bearer` from `NVIDIA_NIM_API_KEY`. The key lives in gitignored `agents/.env` and in the ingest environment. It is not committed, not logged, not a fixture, and not the Nightshift Providers-tab key.
- The body is `{"model","input","input_type","dimensions"}`. `input` is a list of strings.
- Chat completions stay on Nightshift (`meterless/fast`, `meterless/deep`) under ADR 0004. Nightshift is not called for embeddings.
- The distance operator is pgvector cosine distance, `<=>`. It runs in this Postgres and nowhere else. Agents never send `<=>` or `<->` in Zetaris SQL.
- The stored column is `vector(2048)`. The ANN index is HNSW on `(embedding::halfvec(2048))` with `halfvec_cosine_ops`. The search uses the same expression. Do not truncate the model output to 2000.
- If the installed pgvector refuses the halfvec index, the fallback query is an exact `ORDER BY embedding <=> $1::vector` with no ANN index. The operator stays `<=>` in Postgres either way.
- `PGVECTOR_PASSWORD` stays the characters `${PGVECTOR_PASSWORD}` in `zetaris/migrations/`. `compose.yaml` is not edited.
- Git tracks `corpus/manifest.yaml` and `corpus/pdf/`. Git ignores `corpus/.embed-cache/` and `corpus/fetched/`. The pgvector volume `floodsense-app_pgdata` is a Docker volume, not a path in the tree.
- Embedding cache path: `corpus/.embed-cache/nvidia/llama-nemotron-embed-1b-v2/2048/{passage|query}/{sha256}.json`, where `{sha256}` is the SHA-256 of the UTF-8 text that was embedded.
- `storage` is `full_text` for every document in this corpus.
- Every citable paragraph sets `page` ≥ 1, `paragraph` ≥ 1, and `lines`. `section` may be null and does not replace `page`.
- The quote is a verbatim slice of `text`, at most 600 characters. `content_sha256` is the lower-case SHA-256 hex of the quote as UTF-8. `text_sha256` is the SHA-256 hex of the full chunk `text` as UTF-8.
- `k` is an integer from 1 to 20.
- H-MEM's 64-dimension FNV-1a stub and the World Model are not the document store and are not modified.
- Branch names are `feat/` only. Do not open a `cursor/` branch. Do not merge these pull requests in the implementation run. Each pull request adds a line under `## [Unreleased]` in `CHANGELOG.md`.
- `tasks.py` stays stdlib only. No `shell=True`. No `nvapi-` string in the tree.

## File map

| Path | Pull request | Responsibility |
| --- | --- | --- |
| `corpus/manifest.yaml` | 1 | Tracked list of documents |
| `corpus/pdf/` | 1 | Redistributable copies named by the manifest |
| `corpus/README.md` | 1 | What the copies are, and what the fetch command does |
| `scripts/rag_corpus.py` | 1 | Parse the manifest, check sha256, download `placement: fetch` |
| `scripts/tests/test_rag_corpus.py` | 1 | Parser, fetch, and the committed hashes |
| `tasks.py` | 1 | `fetch-rag-corpus` subcommand |
| `docs/legal/sources.md` | 1 | EMSR517, HESS, NHESS, EasyxLab S19, and the stored EMSR773 map |
| `pgvector/migrations/001_rag_chunks.sql` | 2 | Empty `rag.chunks` table and the halfvec HNSW index |
| `zetaris/migrations/044_register_pgvector_rag_chunks.sql` | 2 | JDBC registration, password left as `${PGVECTOR_PASSWORD}` |
| `ingestion/.env.example` | 2 | Empty `PGVECTOR_PASSWORD=` name |
| `scripts/tests/test_rag_schema.py` | 2 | The SQL matches the spec and holds no literal password |
| `agents/floodsense_agents/nim_embed.py` | 3 | NIM client and the embed cache |
| `scripts/rag_ingest.py` | 3 | Chunk hierarchy and insert into `rag.chunks` |
| `agents/tests/test_nim_embed.py` | 3 | Cache, request body, and key redaction |
| `scripts/tests/test_rag_ingest.py` | 3 | Paragraph split, page ids, no `retrieve_docs` |
| `agents/floodsense_agents/retrieve_docs.py` | 4 | `retrieve_docs` and the quote builder |
| `agents/floodsense_agents/nodes/judge.py` | 4 | Substring check against `text` / `text_sha256` |
| `agents/floodsense_agents/nodes/investigator.py` | 4 | One optional call when the flag is on |
| `agents/floodsense_agents/graph.py` | 4 | Registration when `ff_rag_docs` is on |
| `api/app/project.py` | 4 | Copy `locator` and `chunk_id` onto the wire citation |

Task 1 is implemented on `feat/rag-corpus-fetch`. Tasks 2, 3, and 4 each branch from `main` after the previous pull request has merged. They do not stack onto an open branch.

---

### Task 1: Corpus manifest and `fetch-rag-corpus`

**Files:**
- Create: `corpus/manifest.yaml`
- Create: `corpus/pdf/emsr773-aoi03-delineation-map.pdf`
- Create: `corpus/pdf/emsr517-aoi15-grading-map.pdf`
- Create: `corpus/pdf/hess-29-6715-2025.pdf`
- Create: `corpus/pdf/nhess-23-1287-2023.pdf`
- Create: `corpus/pdf/easyxlab-s19.html`
- Create: `corpus/README.md`
- Create: `scripts/rag_corpus.py`
- Create: `scripts/tests/test_rag_corpus.py`
- Modify: `tasks.py` (`build_parser`, `main`, `cmd_fetch_rag_corpus`)
- Modify: `tests/test_tasks.py` (missing-manifest case)
- Modify: `docs/legal/sources.md` (rows 8–11 and the EMSR773 map note)
- Modify: `CHANGELOG.md` under `## [Unreleased]`
- Modify: `docs/OWNERSHIP.md` (the corpus row now exists)
- Confirm, do not duplicate: `.gitignore` already lists `corpus/.embed-cache/` and `corpus/fetched/`

**Interfaces:**
- Consumes: nothing from a later task. The design spec's manifest fields are the contract.
- Produces: `rag_corpus.parse_manifest(text: str) -> list[dict[str, object]]` and `rag_corpus.fetch_rag_corpus(root: Path, *, opener: Callable[[str], bytes] | None = None) -> int`. Each dict has `doc_id: str`, `title: str`, `publisher: str`, `url: str`, `licence: str`, `attribution: str`, `sha256: str`, `tier: int`, `event_id: str | None`, `path: str`, `placement: str`. `opener` is used only for `placement: fetch`. Return `0` on success and `1` on a manifest or hash error. `python tasks.py fetch-rag-corpus` calls `fetch_rag_corpus` on the repo root and returns that code.

Committed documents, bytes fetched on 26 Oct 2026:

| doc_id | tier | event_id | placement | path | sha256 | url |
| --- | --- | --- | --- | --- | --- | --- |
| `emsr773-aoi03-del` | 1 | `EMSR773` | `git` | `pdf/emsr773-aoi03-delineation-map.pdf` | `ebc8b28215ea5b110814aeb279ae715f05b9e18813546cf80b7123529750d42d` | `https://mapping.emergency.copernicus.eu/activations/EMSR773` |
| `emsr517-aoi15-gra` | 1 | `EMSR517` | `git` | `pdf/emsr517-aoi15-grading-map.pdf` | `53731bb424a814e0202980ed40428b1fe7b5bf49e7b9f25b8eebfca0aa47bcdb` | `https://mapping.emergency.copernicus.eu/activations/EMSR517` |
| `hess-29-6715-2025` | 2 | `EMSR773` | `git` | `pdf/hess-29-6715-2025.pdf` | `9fc5796a8a1243099401fb97271e35d1c2213b06aa250ceb437b1b68a2ff8319` | `https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf` |
| `nhess-23-1287-2023` | 2 | `EMSR517` | `git` | `pdf/nhess-23-1287-2023.pdf` | `251bf798c20a4abe313f718ed72fe48369b5779c82affe223deb58815e29787c` | `https://nhess.copernicus.org/articles/23/1287/2023/nhess-23-1287-2023.pdf` |
| `easyxlab-s19` | 2 | `EMSR773` | `git` | `pdf/easyxlab-s19.html` | `4c658dc3d9e4b6fa4200fb653b68f065721d079fe4c8b11f0710d5e771fa3e0c` | `https://easybyte.es/lab/studies/s19/paper/` |

The EMSR773 PDF is `Maps/EMSR773_AOI03_DEL_PRODUCT_29000_map_v1.pdf` taken out of `EMSR773_AOI03_DEL_PRODUCT_v1.zip`. The zip and its shapefiles are not committed. The EMSR517 PDF is the public S3 grading map for Bad Neuenahr-Ahrweiler (AOI15). EasyxLab S19 is the HTML of the paper page with the Cloudflare challenge script and Web Analytics beacon removed. It does not contain the Generalitat geometry. Tier 3 has zero files. There is no `placement: fetch` row in this manifest. The command still implements fetch for a later bulletin.

Attribution strings, copied from the spec:

- `Copernicus Emergency Management Service (© 2024 European Union), EMSR773`
- `Copernicus Emergency Management Service (© 2021 European Union), EMSR517`
- `Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0, https://doi.org/10.5194/hess-29-6715-2025`
- `Ludwig, Mohr, and co-authors (2023), CC BY 4.0, https://doi.org/10.5194/nhess-23-1287-2023`
- `EasyxLab (2026), Study S19, CC BY 4.0, https://easybyte.es/lab/studies/s19/paper/`

Licence values: `CEMS On-Demand Mapping terms` for both Copernicus maps, `CC-BY-4.0` for the three Tier 2 documents.

Titles:

- `[EMSR773] Horta Sud (AOI03): Delineation Map`
- `[EMSR517] Bad Neuenahr-Ahrweiler (AOI15): Grading Map`
- `Torrential rainfall in Valencia, Spain, recorded by personal weather stations preceding and during the 29 October 2024 floods`
- `A multi-disciplinary analysis of the exceptional flood event of July 2021 in central Europe – Part 2: Historical context and relation to climate change`
- `What the maps did not show: dwellings inside the observed extent of the October 2024 DANA in Valencia, and the official flood maps`

Publishers: `Copernicus Emergency Management Service`, `Copernicus Publications`, `EasyxLab`.

- [x] **Step 1: Write the failing parser and fetch tests**

Create `scripts/tests/test_rag_corpus.py`. It inserts `scripts/` on `sys.path` and imports `rag_corpus`. Cover at least:

- a quoted title round-trips, `tier` is an `int`, and `event_id` is the string `EMSR773`
- tier 3 accepts `event_id: null`
- licence `CC-BY-NC-ND-4.0` raises `CorpusError`
- an `http://` URL raises `CorpusError`
- path `pdf/../../secrets.env` raises `CorpusError`
- a git file whose sha256 matches does not call `opener`
- a git sha256 mismatch returns 1 and does not call `opener`
- a fetch entry writes `corpus/fetched/<name>`, and a second run with the same bytes does not call `opener`
- a fetch body with the wrong sha256 returns 1 and leaves no file
- the module source contains neither `integrate.api.nvidia.com`, `input_type`, `nvapi-`, nor `docker`
- `.gitignore` contains `corpus/.embed-cache/` and `corpus/fetched/`
- `fetch_rag_corpus` on the repo root, with an `opener` that raises `AssertionError`, returns 0, and the manifest `doc_id` order is `emsr773-aoi03-del`, `emsr517-aoi15-gra`, `hess-29-6715-2025`, `nhess-23-1287-2023`, `easyxlab-s19`

- [x] **Step 2: Run the tests and see them fail**

Run: `python3 -m unittest discover -s scripts/tests -p test_rag_corpus.py -v`

Expected: `ModuleNotFoundError: No module named 'rag_corpus'`

- [x] **Step 3: Implement the manifest parser and the fetch command**

`scripts/rag_corpus.py` is stdlib only. `parse_manifest` accepts a YAML subset: comments and blank lines are ignored, each document starts with `- doc_id:`, later keys are indented two spaces, values are `null`, an integer, a double-quoted string, or a bare string. Required keys are `doc_id`, `title`, `publisher`, `url`, `licence`, `attribution`, `sha256`, `tier`, `event_id`, `path`, `placement`.

Reject a licence matching `BY-NC`, `BY-ND`, `NonCommercial`, or `NoDerivatives`. Require `https://` and reject `@` in the URL. `sha256` is 64 lowercase hex characters. `tier` is 1, 2, or 3. Tiers 1 and 2 require `event_id` of `EMSR773` or `EMSR517`. Tier 3 may use `null`. `placement: git` paths stay under `pdf/`. `placement: fetch` paths stay under `fetched/`. `..`, a leading slash, and a backslash are rejected. Duplicate `doc_id` or `path` is an error. An empty manifest is an error.

`fetch_rag_corpus` reads `corpus/manifest.yaml`. For `git`, the file must already exist and hash to `sha256`. It is never downloaded. For `fetch`, a file that already hashes correctly is kept. Otherwise `opener(url)` (default: urllib with `User-Agent: floodsense-rag-corpus/1.0`, timeout 120 seconds, cap `1024 * 1024 * 1024` bytes) must return bytes whose sha256 matches. Write those bytes via a `.partial` sibling and `replace`. A mismatch deletes the partial and leaves any previous file in place. Success prints `rag corpus: N checked, M fetched` and returns 0. Failures print `rag corpus: ...` on stderr and return 1.

`tasks.py` loads that module with `importlib.util` from `scripts/rag_corpus.py` and dispatches `fetch-rag-corpus`. The help text says the command checks sha256, downloads placement fetch into `corpus/fetched/`, and does not embed or start Docker. The source of `tasks.py` must not contain the string `python3`.

`docs/legal/sources.md` gains rows 8 (EMSR517), 9 (HESS), 10 (NHESS), and 11 (EasyxLab S19), each stating that full text may be stored, plus a note under EMSR773 naming the Horta Sud PDF and stating that the product zip is not stored.

- [x] **Step 4: Run the tests and see them pass**

Run: `python3 -m unittest discover -s scripts/tests -p test_rag_corpus.py -v`

Expected: `OK`

Run: `python3 -m unittest tests.test_tasks.TaskTest.test_fetch_rag_corpus_reports_a_missing_manifest -v`

Expected: `OK`, stderr contains `corpus/manifest.yaml`

- [x] **Step 5: Commit**

```bash
git add corpus scripts/rag_corpus.py scripts/tests/test_rag_corpus.py tasks.py tests/test_tasks.py docs/legal/sources.md docs/OWNERSHIP.md CHANGELOG.md docs/superpowers/plans/2026-10-26-rag-layer-c-v014-implementation.md
git commit -m "feat: add the layer (c) corpus and fetch-rag-corpus"
```

Do not commit `.env`, `corpus/fetched/`, or `corpus/.embed-cache/`.

---

### Task 2: `rag.chunks` and the Zetaris JDBC registration

**Files:**
- Create: `pgvector/migrations/001_rag_chunks.sql`
- Create: `zetaris/migrations/044_register_pgvector_rag_chunks.sql`
- Create: `scripts/tests/test_rag_schema.py`
- Modify: `ingestion/.env.example` (empty `PGVECTOR_PASSWORD=`)
- Modify: `pgvector/README.md` (one paragraph: the schema file exists, apply it with `psql` against `127.0.0.1:15432`, the password stays in `pgvector/.env`)
- Modify: `CHANGELOG.md` under `## [Unreleased]`
- Do not modify: `compose.yaml`, `scripts/rag_corpus.py`, `agents/floodsense_agents/nodes/investigator.py`

**Interfaces:**
- Consumes: nothing from Task 1 at runtime. The table is empty.
- Produces: Postgres table `rag.chunks` and Zetaris datasource `PGVECTOR_RAG` whose registered table is queried as `PGVECTOR_RAG.chunks`. Columns used by Tasks 3 and 4: `chunk_id text` primary key, `parent_chunk_id text` null on the document row, `path text`, `level text` in `doc|page|section|paragraph`, `doc_id text`, `tier smallint`, `event_id text` null allowed, `title text`, `source_url text`, `publisher text`, `licence text`, `attribution text`, `page integer` null on a document row, `paragraph integer`, `lines text`, `section text`, `text text`, `text_sha256 text`, `embedding vector(2048)` null except on `level = paragraph`, `embed_model text` null unless `embedding` is set, and then it equals `nvidia/llama-nemotron-embed-1b-v2`.

- [x] **Step 1: Write the failing SQL contract test**

```python
def test_postgres_index_matches_the_spec(self) -> None:
    sql = (ROOT / "pgvector" / "migrations" / "001_rag_chunks.sql").read_text(encoding="utf-8")
    self.assertIn("CREATE TABLE rag.chunks", sql)
    self.assertIn("embedding vector(2048)", sql)
    self.assertIn(
        "CREATE INDEX rag_chunks_embed_hnsw\n"
        "  ON rag.chunks\n"
        "  USING hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)\n"
        "  WHERE level = 'paragraph' AND embedding IS NOT NULL;",
        sql,
    )
    self.assertIn("embedding::halfvec(2048) <=> $1::halfvec(2048)", sql)
    self.assertIn("ORDER BY embedding <=> $1::vector", sql)
    self.assertNotIn("nvapi-", sql)


def test_zetaris_registration_keeps_the_password_placeholder(self) -> None:
    sql = (ROOT / "zetaris" / "migrations" / "044_register_pgvector_rag_chunks.sql").read_text(
        encoding="utf-8"
    )
    self.assertIn('password "${PGVECTOR_PASSWORD}"', sql)
    self.assertIn("REGISTER DATASOURCE TABLE \"chunks\" FROM PGVECTOR_RAG", sql)
    self.assertIn('schema "rag"', sql)
    self.assertNotIn("<=>", sql)
    self.assertNotIn("<->", sql)
    self.assertNotIn("local-dev-only", sql)
    self.assertNotIn("nvapi-", sql)
```

- [x] **Step 2: Run the test and see it fail**

Run: `python3 -m unittest scripts.tests.test_rag_schema -v`

Expected: `FileNotFoundError` on `pgvector/migrations/001_rag_chunks.sql`

- [x] **Step 3: Write the Postgres migration**

`pgvector/migrations/001_rag_chunks.sql`:

```sql
-- Apply to the rag-profile Postgres on 127.0.0.1:15432. Not a Zetaris file.
-- The password stays in pgvector/.env. This file has no password.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE rag.chunks (
  chunk_id text PRIMARY KEY,
  parent_chunk_id text REFERENCES rag.chunks (chunk_id),
  path text NOT NULL,
  level text NOT NULL CHECK (level IN ('doc', 'page', 'section', 'paragraph')),
  doc_id text NOT NULL,
  tier smallint NOT NULL CHECK (tier IN (1, 2, 3)),
  event_id text,
  title text NOT NULL,
  source_url text NOT NULL,
  publisher text NOT NULL,
  licence text NOT NULL,
  attribution text NOT NULL,
  page integer,
  paragraph integer,
  lines text,
  section text,
  text text NOT NULL,
  text_sha256 text NOT NULL,
  embedding vector(2048),
  embed_model text,
  CONSTRAINT rag_chunks_embed_model CHECK (
    (embedding IS NULL AND embed_model IS NULL)
    OR (
      embedding IS NOT NULL
      AND level = 'paragraph'
      AND embed_model IS NOT NULL
      AND embed_model = 'nvidia/llama-nemotron-embed-1b-v2'
    )
  ),
  CONSTRAINT rag_chunks_paragraph_locator CHECK (
    level <> 'paragraph'
    OR (
      page IS NOT NULL AND page >= 1
      AND paragraph IS NOT NULL AND paragraph >= 1
      AND lines IS NOT NULL AND lines <> ''
    )
  )
);

CREATE INDEX rag_chunks_embed_hnsw
  ON rag.chunks
  USING hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)
  WHERE level = 'paragraph' AND embedding IS NOT NULL;

-- search (Postgres only, not Zetaris):
-- SELECT chunk_id, (embedding::halfvec(2048) <=> $1::halfvec(2048)) AS distance
-- FROM rag.chunks
-- WHERE level = 'paragraph'
--   AND embedding IS NOT NULL
--   AND ($2::text IS NULL OR event_id = $2)
-- ORDER BY embedding::halfvec(2048) <=> $1::halfvec(2048)
-- LIMIT $3;
--
-- fallback if the installed pgvector refuses the halfvec index:
-- SELECT chunk_id, (embedding <=> $1::vector) AS distance
-- FROM rag.chunks
-- WHERE level = 'paragraph'
--   AND embedding IS NOT NULL
--   AND ($2::text IS NULL OR event_id = $2)
-- ORDER BY embedding <=> $1::vector
-- LIMIT $3;
```

No `INSERT`. The table stays empty in this pull request.

- [x] **Step 4: Write the Zetaris registration**

`zetaris/migrations/044_register_pgvector_rag_chunks.sql` has two statements split by a line that is exactly `-- statement`. It has no `-- view:` header, because verify would look for a SCHEMASTORE view and this file does not create one. Lightning SQL from the Zetaris guide: `jdbcdriver`, `jdbcurl`, `username`, `password`, `schema`.

```sql
-- JDBC registration of rag.chunks. Password stays a placeholder.
-- Agents must not send the cosine or L2 distance operators to Zetaris. Ranking stays in Postgres.
CREATE DATASOURCE PGVECTOR_RAG DESCRIBE BY "pgvector rag chunks" OPTIONS (
  jdbcdriver "org.postgresql.Driver",
  jdbcurl "jdbc:postgresql://host.docker.internal:15432/floodsense",
  username "floodsense",
  password "${PGVECTOR_PASSWORD}",
  schema "rag"
)
-- statement
REGISTER DATASOURCE TABLE "chunks" FROM PGVECTOR_RAG
```

Append this line to `ingestion/.env.example`:

```text
# Password of the rag-profile Postgres. Migration 044 keeps ${PGVECTOR_PASSWORD}.
PGVECTOR_PASSWORD=
```

The value is filled only in gitignored `ingestion/.env`. Do not copy `local-dev-only` into the SQL file.

- [x] **Step 5: Run the tests**

Run: `python3 -m unittest scripts.tests.test_rag_schema -v`

Expected: `OK`

Run: `python3 scripts/zetaris_sync.py sync --dry-run`

Expected: exit 0. The new file is parsed. Nothing is sent.

- [x] **Step 6: Commit**

```bash
git add pgvector/migrations/001_rag_chunks.sql zetaris/migrations/044_register_pgvector_rag_chunks.sql scripts/tests/test_rag_schema.py ingestion/.env.example pgvector/README.md CHANGELOG.md
git commit -m "feat: add rag.chunks and the Zetaris JDBC registration"
```

---

### Task 3: NIM embeddings client and ingest

**Files:**
- Create: `agents/floodsense_agents/nim_embed.py`
- Create: `agents/tests/test_nim_embed.py`
- Create: `scripts/rag_ingest.py`
- Create: `scripts/tests/test_rag_ingest.py`
- Modify: `agents/.env.example` (empty `NVIDIA_NIM_API_KEY=` and empty `NIM_EMBEDDINGS_URL=`)
- Modify: `agents/requirements.txt` (add `psycopg>=3.2,<4`)
- Modify: `requirements-dev.txt` (add `pypdf>=5.1,<6`)
- Modify: `CHANGELOG.md`
- Do not create: `retrieve_docs`, and do not change `FF_RAG_DOCS=false`

**Interfaces:**
- Consumes: Task 1 `parse_manifest` / manifest paths. Task 2 columns. A paragraph is over the model limit when `len(text.encode("utf-8")) > 8192 * 4`.
- Produces:
  - `nim_embed.MODEL = "nvidia/llama-nemotron-embed-1b-v2"`
  - `nim_embed.DIMENSIONS = 2048`
  - `nim_embed.DEFAULT_URL = "https://integrate.api.nvidia.com/v1/embeddings"`
  - `nim_embed.cache_path(root: Path, input_type: str, text: str) -> Path`
  - `nim_embed.embed_texts(texts: list[str], input_type: str, *, root: Path, api_key: str, url: str = DEFAULT_URL, opener: Callable[[str, dict, bytes], dict] | None = None) -> list[list[float]]`
  - `rag_ingest.ingest(root: Path, *, embedder, writer) -> int`
  - `embedder(texts: list[str], input_type: str) -> list[list[float]]` is called with `input_type="passage"` only.
  - `writer(rows: list[dict]) -> None` receives document, then page or section, then paragraph rows. Paragraph rows set `embedding` and `embed_model`. Parent rows set both to `None`.

`opener(url, headers, body) -> dict` returns the NIM JSON `{"data": [{"index": int, "embedding": list[float]}, ...]}`. The default opener uses urllib, sets `Authorization: Bearer <api_key>`, and on HTTP failure raises `EmbedError` whose message is `NIM embeddings HTTP <code>` and does not contain the key.

- [ ] **Step 1: Write the failing embed test**

```python
def test_cache_hit_does_not_call_nim(self) -> None:
    root = Path(self.tmp.name)
    text = "Paiporta recorded rain."
    path = nim_embed.cache_path(root, "passage", text)
    path.parent.mkdir(parents=True)
    vector = [0.0] * 2047 + [1.0]
    path.write_text(json.dumps({"embedding": vector}), encoding="utf-8")

    def opener(url, headers, body):
        raise AssertionError(body)

    got = nim_embed.embed_texts([text], "passage", root=root, api_key="test-key", opener=opener)
    self.assertEqual(got, [vector])
    self.assertEqual(
        path.relative_to(root).as_posix(),
        "corpus/.embed-cache/nvidia/llama-nemotron-embed-1b-v2/2048/passage/"
        + hashlib.sha256(text.encode()).hexdigest()
        + ".json",
    )


def test_request_body_and_key_stay_out_of_errors(self) -> None:
    root = Path(self.tmp.name)

    def opener(url, headers, body):
        self.assertEqual(url, nim_embed.DEFAULT_URL)
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        payload = json.loads(body)
        self.assertEqual(payload["model"], "nvidia/llama-nemotron-embed-1b-v2")
        self.assertEqual(payload["input_type"], "query")
        self.assertEqual(payload["dimensions"], 2048)
        self.assertEqual(payload["input"], ["where was the rain"])
        raise nim_embed.EmbedError("NIM embeddings HTTP 401")

    with self.assertRaises(nim_embed.EmbedError) as caught:
        nim_embed.embed_texts(
            ["where was the rain"], "query", root=root, api_key="test-key", opener=opener
        )
    self.assertNotIn("test-key", str(caught.exception))
```

- [ ] **Step 2: Run it and see it fail**

Run: `python3 -m unittest agents.tests.test_nim_embed -v`

Expected: `ModuleNotFoundError` for `nim_embed`. The agents tests add `agents/` to `sys.path` the same way `agents/tests/test_judge.py` does.

- [ ] **Step 3: Implement the client**

`cache_path` joins `root / "corpus" / ".embed-cache" / "nvidia" / MODEL / "2048" / input_type / f"{sha256}.json"`. `input_type` must be `passage` or `query`. A cache file is a hit only when `embedding` is a list of 2048 numbers. A miss calls `opener` once for the missing texts, writes one JSON file per text, and returns vectors in input order using `data[].index`. Do not log `api_key` or the request body.

- [ ] **Step 4: Write the failing ingest test**

```python
def test_long_paragraph_splits_on_lines_and_parents_have_no_embedding(self) -> None:
    line = "word " * 10
    # 8192 * 4 bytes is the limit. Two blocks of lines cross it.
    text = "\n".join([line] * 4000)
    parts = rag_ingest.split_paragraph(text)
    self.assertGreater(len(parts), 1)
    self.assertTrue(all(len(piece.encode("utf-8")) <= 8192 * 4 for piece, _lines in parts))
    start, end = (int(part) for part in parts[0][1].split("-"))
    self.assertEqual(start, 1)
    self.assertEqual(end - start + 1, parts[0][0].count("\n") + 1)
    rows = rag_ingest.rows_for_document(
        {
            "doc_id": "easyxlab-s19",
            "title": "S19",
            "publisher": "EasyxLab",
            "url": "https://easybyte.es/lab/studies/s19/paper/",
            "licence": "CC-BY-4.0",
            "attribution": "EasyxLab (2026), Study S19, CC BY 4.0",
            "tier": 2,
            "event_id": "EMSR773",
        },
        pages=None,
        sections=[("Unmapped places", ["Outside every zone."])],
    )
    kinds = [row["level"] for row in rows]
    self.assertEqual(kinds[0], "doc")
    self.assertIn("section", kinds)
    self.assertIn("paragraph", kinds)
    para = next(row for row in rows if row["level"] == "paragraph")
    self.assertGreaterEqual(para["page"], 1)
    self.assertGreaterEqual(para["paragraph"], 1)
    self.assertTrue(para["lines"])
    self.assertIsNone(next(row["embedding"] for row in rows if row["level"] == "doc"))
    self.assertEqual(para["embed_model"], "nvidia/llama-nemotron-embed-1b-v2")
    self.assertEqual(len(para["embedding"]), 2048)
    self.assertNotIn("retrieve_docs", Path(rag_ingest.__file__).read_text(encoding="utf-8"))
```

The embedder double in that test returns `[[0.0] * 2047 + [1.0]]` for each passage batch. `split_paragraph` records `lines` as a 1-based range inside the original paragraph (`3-5` when the slice is original lines 3 through 5). A single line that itself exceeds `8192 * 4` UTF-8 bytes is cut on UTF-8 boundaries into sibling slices, each tagged `i-i` for that source line.

`rows_for_document` assigns PDF pages as `doc_id/p{page}/para{n}` with `page` equal to the 1-based PDF page. Section text (EasyxLab S19 and any Tier 3 bulletin) uses `doc_id/s{n}/para{k}`, sets `section` to the heading, and sets `page` to that section's 1-based index so a section-only paragraph stays citable. A page with no extracted text gets a page row and no paragraph row. `chunk_id` equals `path` and must be at most 128 characters. `text_sha256` is SHA-256 of `text` as UTF-8.

- [ ] **Step 5: Implement ingest and run the tests**

`scripts/rag_ingest.py` loads the manifest through `rag_corpus.parse_manifest`. PDF bytes go through `pypdf.PdfReader.extract_text`. HTML uses `html.parser`: `h1` and `h2` start a section, each `p` is a paragraph, `script` and `style` are ignored. `ingest` calls `embedder` with `passage` only, then `writer`. The default writer opens `PGVECTOR_DSN`, refuses to print it, deletes existing rows for each `doc_id`, and inserts parents before children. A missing `PGVECTOR_DSN` returns 1 before any NIM call. `python3 scripts/rag_ingest.py` is the command. It reads `NVIDIA_NIM_API_KEY` from the environment.

Run: `python3 -m unittest agents.tests.test_nim_embed scripts.tests.test_rag_ingest -v`

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add agents/floodsense_agents/nim_embed.py agents/tests/test_nim_embed.py scripts/rag_ingest.py scripts/tests/test_rag_ingest.py agents/.env.example agents/requirements.txt requirements-dev.txt CHANGELOG.md
git commit -m "feat: embed the corpus into rag.chunks"
```

---

### Task 4: `retrieve_docs`, Investigator registration, Judge substring check

**Files:**
- Create: `agents/floodsense_agents/retrieve_docs.py`
- Create: `agents/tests/test_retrieve_docs.py`
- Modify: `agents/floodsense_agents/models.py` (`Citation.chunk_id: str | None = None`)
- Modify: `agents/floodsense_agents/state.py` (`Deps.retrieve_docs` default `None`)
- Modify: `agents/floodsense_agents/graph.py` (`ff_rag_docs` argument)
- Modify: `agents/floodsense_agents/nodes/investigator.py` (one optional call)
- Modify: `agents/floodsense_agents/nodes/judge.py` (`layer_c_matches_passage`)
- Modify: `agents/tests/test_judge.py`
- Modify: `api/app/project.py` (`_project_citations` copies `locator` and `chunk_id`)
- Modify: `api/tests/test_contract_projection.py`
- Modify: `CHANGELOG.md`
- Do not change: `agents/.env.example` line `FF_RAG_DOCS=false`

**Interfaces:**
- Consumes: Task 3 `embed_texts(..., input_type="query")`. Task 2 search SQL and `PGVECTOR_RAG.chunks`.
- Produces:
  - `quote_from_text(text: str, paragraph_lines: str) -> tuple[str, str]` returns `(quote, lines)`. When `len(text) <= 600` and the text has one line, lines is `1-1` and the quote is `text`. When `len(text) <= 600` and the text has more than one line, the quote is `text` and lines is `paragraph_lines`. When `text` is longer, the quote is a leading line range of at most 600 characters and lines is that 1-based range inside the chunk (`1-2`). `content_sha256` is `hashlib.sha256(quote.encode()).hexdigest()`.
  - `retrieve_docs(query: str, k: int, filters: dict | None, *, embedder, search, hydrate) -> RetrieveResult`
  - `RetrieveResult` has `citations: list[dict]` and `error: str | None`.
  - `search(vector: list[float], event_id: str | None, k: int) -> list[tuple[str, float]]` returns `(chunk_id, distance)` in ANN order. The default search runs the halfvec statement. If that statement fails because halfvec is unavailable, it runs the exact `embedding <=> $1::vector` statement. `$1` is the query embedding. `$2` is `event_id` or NULL. `$3` is `k`.
  - `hydrate(chunk_ids: list[str]) -> tuple[str, list[dict]]` returns `(query_id, rows)`. The default calls Zetaris `run_sql` with a `SELECT` of `chunk_id, text, text_sha256, title, source_url, publisher, licence, attribution, page, paragraph, lines, section` from `PGVECTOR_RAG.chunks` and no `embedding` column and no `<=>`. Chunk ids must match `^[A-Za-z0-9][A-Za-z0-9_./-]{0,127}$` or the call returns `error` and no citation.
  - `build_graph(..., ff_rag_docs: bool | None = None)`. `None` reads `settings.ff_rag_docs`, which defaults to false. When the flag is on and `deps.retrieve_docs` is `None`, set it to the live callable. When the flag is off, set `deps.retrieve_docs` to `None`.

- [ ] **Step 1: Write the failing retrieve and judge tests**

```python
def test_empty_search_returns_no_citations(self) -> None:
    def hydrate(ids):
        raise AssertionError(ids)

    result = retrieve_docs(
        "rain in Paiporta",
        4,
        {"event_id": "EMSR773"},
        embedder=lambda texts, input_type: [[0.0] * 2048],
        search=lambda vector, event_id, k: [],
        hydrate=hydrate,
    )
    self.assertEqual(result.citations, [])
    self.assertIsNone(result.error)


def test_k_out_of_range_is_a_tool_error(self) -> None:
    def unused(*_args, **_kwargs):
        raise AssertionError("k is rejected before embed, search, or hydrate")

    result = retrieve_docs(
        "q", 0, {"event_id": "EMSR773"}, embedder=unused, search=unused, hydrate=unused
    )
    self.assertEqual(result.citations, [])
    self.assertIn("1 to 20", result.error)


def test_quote_is_a_substring_and_hashes(self) -> None:
    text = "line one\nline two stays under six hundred"
    row = {
        "chunk_id": "hess-29-6715-2025/p12/para3",
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "title": "HESS",
        "source_url": "https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf",
        "publisher": "Copernicus Publications",
        "licence": "CC-BY-4.0",
        "attribution": "Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0",
        "page": 12,
        "paragraph": 3,
        "lines": "1-2",
        "section": None,
    }

    def embedder(texts, input_type):
        self.assertEqual(input_type, "query")
        return [[0.1] * 2048]

    result = retrieve_docs(
        "rainfall",
        1,
        {"event_id": "EMSR773"},
        embedder=embedder,
        search=lambda vector, event_id, k: [(row["chunk_id"], 0.2)],
        hydrate=lambda ids: ("qid-9", [row]),
    )
    citation = result.citations[0]
    self.assertEqual(citation["query_id"], "qid-9")
    self.assertEqual(citation["storage"], "full_text")
    self.assertIn(citation["quote"], text)
    self.assertLessEqual(len(citation["quote"]), 600)
    self.assertEqual(citation["content_sha256"], hashlib.sha256(citation["quote"].encode()).hexdigest())
    self.assertEqual(citation["locator"]["page"], 12)
    self.assertEqual(citation["chunk_id"], row["chunk_id"])
    self.assertNotIn("distance", citation)


def test_missing_hydrate_row_is_dropped(self) -> None:
    kept = {
        "chunk_id": "kept",
        "text": "The Ahr rose at Altenahr.",
        "text_sha256": hashlib.sha256(b"The Ahr rose at Altenahr.").hexdigest(),
        "title": "EMSR517",
        "source_url": "https://mapping.emergency.copernicus.eu/activations/EMSR517",
        "publisher": "Copernicus Emergency Management Service",
        "licence": "CEMS On-Demand Mapping terms",
        "attribution": "Copernicus Emergency Management Service (© 2021 European Union), EMSR517",
        "page": 1,
        "paragraph": 1,
        "lines": "1-1",
        "section": None,
    }
    result = retrieve_docs(
        "q",
        2,
        {"event_id": "EMSR517"},
        embedder=lambda texts, input_type: [[0.0] * 2048],
        search=lambda vector, event_id, k: [("kept", 0.1), ("gone", 0.2)],
        hydrate=lambda ids: ("qid", [kept]),
    )
    self.assertEqual([c["chunk_id"] for c in result.citations], ["kept"])


def test_layer_c_must_be_a_substring_of_text(self) -> None:
    text = "The gauge at Altenahr rose."
    digest = hashlib.sha256(text.encode()).hexdigest()
    quote = "The gauge at Altenahr rose."
    claim = Claim(
        claim_id="C1",
        text="Altenahr rose.",
        citations=[
            Citation(citation_id="C1-a1", claim_id="C1", layer="a", query_id="q1"),
            Citation(
                citation_id="C1-c1",
                claim_id="C1",
                layer="c",
                query_id="q1",
                quote=quote,
                content_sha256=hashlib.sha256(quote.encode()).hexdigest(),
            ),
        ],
    )
    evidence = {
        "q1": Evidence(
            query_id="q1",
            view="PGVECTOR_RAG.chunks",
            sql="SELECT text FROM PGVECTOR_RAG.chunks WHERE chunk_id = 'kept'",
            rows_sample=[{"text": text, "text_sha256": digest, "rain_mm": 1}],
            row_count=1,
            executed_at_utc="2026-10-26T12:00:00Z",
        )
    }
    score = score_claim(claim, evidence, None)
    self.assertTrue(score.citation_faithful)
    bad = claim.model_copy(deep=True)
    bad.citations[1].quote = "This sentence is not in the passage."
    bad.citations[1].content_sha256 = hashlib.sha256(bad.citations[1].quote.encode()).hexdigest()
    self.assertFalse(score_claim(bad, evidence, None).citation_faithful)
    alone = Claim(
        claim_id="C2",
        text="Altenahr rose.",
        citations=[bad.citations[1]],
    )
    self.assertFalse(score_claim(alone, evidence, None).citation_faithful)
```

A layer (c) citation with no layer (a) citation stays unfaithful even when the quote matches. A quote hash that does not match the quote stays unfaithful. A `text_sha256` that is not the hash of `text` stays unfaithful.

- [ ] **Step 2: Run the tests and see them fail**

Run: `python3 -m unittest agents.tests.test_retrieve_docs agents.tests.test_judge -v`

Expected: `retrieve_docs` is not defined, and the new judge assertions fail.

- [ ] **Step 3: Implement the tool and the Judge check**

Order inside `retrieve_docs`:

1. If `k` is not an int in `1..20`, return `RetrieveResult([], "k must be from 1 to 20")`.
2. Read `filters["event_id"]` when present. It must be `EMSR773` or `EMSR517`. Omitting it passes `None` to search.
3. Embed `query` with `input_type="query"`. An embedder exception returns `error` set to the exception text, truncated to 200 characters, and no citations.
4. `search` returns ids and distances. An exception is the same tool error. An empty list returns `RetrieveResult([], None)`.
5. `hydrate` those ids. Drop ids with no row. Do not cite a row with no `query_id`. Do not drop a row because `section` is null when `page` ≥ 1.
6. Build one citation per remaining row, in ANN order. `storage` is `full_text`. The citation dict does not include `distance`.

Judge, replacing the quote-hash line in `score_claim`:

```python
def layer_c_matches_passage(citation: Citation, evidence: dict[str, Evidence]) -> bool:
    if not citation.quote or not citation.content_sha256:
        return False
    if hashlib.sha256(citation.quote.encode()).hexdigest() != citation.content_sha256:
        return False
    ev = evidence.get(citation.query_id or "")
    if ev is None or ev.error or not ev.rows_sample:
        return False
    row = ev.rows_sample[0]
    text = row.get("text")
    digest = row.get("text_sha256")
    if not isinstance(text, str) or not isinstance(digest, str):
        return False
    if hashlib.sha256(text.encode()).hexdigest() != digest:
        return False
    return citation.quote in text
```

```python
for x in c.citations:
    if x.layer == "c" and x.quote and x.content_sha256:
        faithful = faithful and layer_c_matches_passage(x, evidence)
```

`faithful` is still false when there is no layer (a) citation with rows. A layer (c) citation on its own does not pass.

Investigator, inside `make`, after the deterministic chain and the optional model rewrite: if `deps.retrieve_docs` is `None`, do not read `doc_query`. If it is set and `state["request"].get("doc_query")` is a non-empty string, call it once with that query, `k` from `state["request"].get("doc_k", 4)`, and `filters={"event_id": state["event_id"]}`. On `error`, append `retrieve_docs error: ...` to the trace summary and add no citation. On citations, append them to the claim named by `state["request"].get("doc_claim_id")` when that claim exists, otherwise append one fact claim `C-doc` whose text is the query. A request without `doc_query` does not call the tool, including when the flag is on.

`nodes/watchers.py`, `nodes/exposure.py`, and `nodes/skeptic.py` do not mention `retrieve_docs`. Add a test that reads those three files and asserts the name is absent.

`_project_citations` copies `locator` when `page` is an int ≥ 1, and copies `chunk_id` when it is a string of length 1 to 128. It still drops `javascript:` URLs. Add a projection test with one layer (c) citation that has `locator.page` 12, `paragraph` 3, `lines` `1-2`, and `chunk_id` `hess-29-6715-2025/p12/para3`, and assert those fields survive `project_run`.

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest agents.tests.test_retrieve_docs agents.tests.test_judge agents.tests.test_graph -v`

Expected: `OK`. A graph run that does not set `doc_query` never calls a retrieve double that raises `AssertionError`, with `ff_rag_docs=True` and with `ff_rag_docs=False`.

Run: `python3 -m unittest api.tests.test_contract_projection -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add agents/floodsense_agents/retrieve_docs.py agents/floodsense_agents/models.py agents/floodsense_agents/state.py agents/floodsense_agents/graph.py agents/floodsense_agents/nodes/investigator.py agents/floodsense_agents/nodes/judge.py agents/tests/test_retrieve_docs.py agents/tests/test_judge.py api/app/project.py api/tests/test_contract_projection.py CHANGELOG.md
git commit -m "feat: retrieve documents when FF_RAG_DOCS is on"
```

Leave `FF_RAG_DOCS=false` in `agents/.env.example`. Do not tag `v0.14.0`.
