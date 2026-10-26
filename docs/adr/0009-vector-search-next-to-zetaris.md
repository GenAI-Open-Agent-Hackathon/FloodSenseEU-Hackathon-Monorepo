# 0009. Vector search runs in pgvector, next to Zetaris

- Status: Proposed
- Date: 2026-10-24
- Updated: 2026-10-26
- Owner: Urvashi

The gameplan calls this ADR-008. Number 0008 is taken by the CI runner decision, so this is 0009.

## Context

Layer (c) citations need similarity search over document chunks. The gameplan (§7.5) assumed Zetaris has no vector search and listed four things to check on our own Zetaris 2.4.3.1: vector features in the edition, reaching pgvector from the Zetaris containers, how a vector column appears and whether anything is pushed down, and where embeddings come from.

[ADR 0003](0003-zetaris-only-data-path.md) says agents read data only through Zetaris, and that pgvector queries by agents need a later ADR.

## What was checked (24 Oct 2026, local stack)

| Question | Result |
| --- | --- |
| Vector features in Zetaris | None found. The getting-started docs, the Lightning SQL reference and the platform README do not mention vectors or embeddings. The API reference at `:8888/redoc` needs a UI login (an API key gets 401), so it was not searched. |
| Can Zetaris reach pgvector | Yes. The Zetaris driver container reaches `host.docker.internal:15432`. `CREATE DATASOURCE` with the PostgreSQL JDBC driver succeeded, and `REGISTER DATASOURCE TABLE` imported the table. pgvector 0.8.7 from our `rag` profile. |
| How a vector column appears | As `string`, for example `[1,0,0]`. There is no vector type in Zetaris. |
| Vector operators in Zetaris SQL | Not supported, and silently wrong. `embedding <=> '[1,0,0]'` returns `true` or `false`, because Zetaris reads `<=>` as null-safe equality. It is not cosine distance. |
| Pushdown | Only through `CREATE DATASOURCE VIEW ... AS <native SQL>`. The native query runs in PostgreSQL, so `<=>` works there and the view returned the right top-2 with distances. The query vector must be written into the view text, so each search would need its own view. |
| Embeddings source | Not checked on 24 Oct. Needs Ayush: whether Nightshift serves embeddings (`GET /v1/models`), or another local model. The gameplan's desk research says runtime 1.4 serves no `/v1/embeddings`. Closed on 26 Oct: see Decision |

## Decision

Chunks, embeddings and the citation path (document, page, paragraph, licence) live in pgvector, started by `docker compose --profile rag`. The search itself runs in PostgreSQL and returns top-k chunk ids and scores. The same PostgreSQL is registered in Zetaris as a JDBC datasource, so chunk metadata is read and joined with the hazard views through Zetaris, and every citation keeps a Zetaris `query_id`.

Agents never put `<=>` or `<->` in Zetaris SQL.

Updated 2026-10-26. Layer (c) is tool RAG. `v0.14.0` is the ship tag and is not cut here. `v0.11.0` is the retired name and is not a tag. The spec is [../superpowers/specs/2026-10-26-rag-layer-c-design.md](../superpowers/specs/2026-10-26-rag-layer-c-design.md). `v0.13.0` is the demo baseline already tagged on main. `FF_RAG_DOCS` stays off.

Embeddings are `nvidia/nemotron-3.5-embed-1b`, dimension 2048 (it replaced `nvidia/llama-nemotron-embed-1b-v2`, which NIM retired on 2026-08-25; `pgvector/migrations/002_rag_embed_model_nemotron35.sql` moves the check), from NVIDIA NIM `POST /v1/embeddings`. Passages use `input_type: passage`. Queries use `input_type: query`. Nightshift does not serve embeddings, so this call does not go through the Nightshift client. Chat completions stay on Nightshift under [ADR 0004](0004-nightshift-only-llm-calls.md). The NIM key is `NVIDIA_NIM_API_KEY` in a gitignored env file. It is not committed and it is not the key in Nightshift's Providers tab.

Why NIM and why this model. To be confirmed by Ayush (embedding client) and Urvashi (store); until then these are the working reasons, not a measured comparison:

- Why `nvidia/nemotron-3.5-embed-1b` and not the model this ADR first named: NIM retired `nvidia/llama-nemotron-embed-1b-v2` on 2026-08-25 and answers it with HTTP 410 `Gone` (checked 26 Oct 2026), so `rag_ingest` could not embed. `nemotron-3.5-embed-1b` is NVIDIA's current 1B embedder on the same endpoint. It takes the same request (`input_type` `passage` or `query`) and returns 2048 dimensions (checked 26 Oct 2026: HTTP 200, 2048 values), so `rag.chunks` and the halfvec index stay as they are. Only the `embed_model` check moves (`002`), and the corpus is re-embedded.
- Nightshift does not answer embeddings today. On 26 Oct its `GET /v1/models` lists `meterless/embed` (endpoints `chat`, `embeddings`; availability `cloud`) and `nvidia/nemotron-3-embed-1b`, but `POST /v1/embeddings` returns 404 `not_found` for those ids and for `nvidia/llama-nemotron-embed-1b-v2`. So the embedding call needs a provider outside Nightshift. If a later Nightshift serves that route, moving the call onto it is a change to `nim_embed.py` and this ADR, and a re-embed if the model or dimension changes. NIM keeps it on NVIDIA, the same vendor and Nemotron family as the chat lanes, and needs no extra local GPU or container.
- It is a retrieval embedder with separate `passage` and `query` input types, which suits short analyst questions ranked against document paragraphs.
- The corpus mixes English, Spanish (Valencia, EMSR773) and German (Ahr, EMSR517) sources. Multilingual support was a reason for the first model; confirm it on the `nemotron-3.5-embed-1b` model card.
- `scripts/rag_ingest.py` assumes an 8192-token input limit and only splits a paragraph above that. Confirm the limit on the `nemotron-3.5-embed-1b` model card.
- Cost for the hackathon is within the free build.nvidia.com trial credits. A paid product would re-check price, terms and a self-hosted NIM.

Not chosen: the engines' token-hash embedder (not semantic, see `agents/README.md`); a local open model (another container and model download during the build); a non-NVIDIA API (a second vendor key for no gain in the demo). Disclosure: this is the one model call that does not go through Nightshift. The deck and video say "every chat call goes through Nightshift", not "every LLM call".

The stored column is `vector(2048)`. A `vector` HNSW index stops at 2000 dimensions, so the ANN index is HNSW on `embedding::halfvec(2048)` with `halfvec_cosine_ops`. The search expression uses `<=>` in this Postgres. Chunks are hierarchical (`parent_chunk_id`, `path` of document, then page or section, then paragraph). H-MEM's hash stub and the World Model stay claim and hypothesis memory. They are not the document store.

Ranking still returns chunk ids and distances from Postgres. Text, licence, and locator are read through the Zetaris JDBC registration, and every layer (c) citation keeps that `query_id`. The metadata hop is required, not optional.

## Consequences

- This is the exception [ADR 0003](0003-zetaris-only-data-path.md) asks for: agents call pgvector directly for ranking only. Text and metadata still come through Zetaris. Mihir accepts or changes it.
- `zetaris/migrations/044_register_pgvector_rag_chunks.sql` registers datasource `PGVECTOR_RAG` and table `chunks`. The password stays `${PGVECTOR_PASSWORD}`. `PGVECTOR_PASSWORD` in `ingestion/.env` matches `POSTGRES_PASSWORD` in `pgvector/.env`.
- The datasource needs `host.docker.internal:15432` reachable from the Zetaris containers. It is on Docker Desktop for Windows. Linux and WSL are not tested.
- The 26 Oct lock keeps direct pgvector ranking plus a Zetaris hydrate. The earlier fallback, one `CREATE DATASOURCE VIEW` per search with the vector inside the native SQL, stays available only if that lock is reversed. It creates and drops a view on every question.

## Open questions

Settled 2026-10-26. The spec linked above is the record.

- Embeddings: `nvidia/nemotron-3.5-embed-1b` on NVIDIA NIM, dimension 2048. Nightshift does not serve them.
- The Zetaris hop is required. Postgres ranks. Zetaris hydrates text, licence, and locator and supplies `query_id`.

Still open:

- Search `:8888/redoc` for vector features while signed in (Urvashi). The 24 Oct check did not open that page. A vector feature found there does not put `<=>` into Zetaris SQL. ADR 0009 already measured that operator as null-safe equality.
