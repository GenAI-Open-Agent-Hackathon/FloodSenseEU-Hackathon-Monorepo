# 0009. Vector search runs in pgvector, next to Zetaris

- Status: Proposed
- Date: 2026-10-24
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
| Embeddings source | Not checked. Needs Ayush: whether Nightshift serves embeddings (`GET /v1/models`), or another local model. The gameplan's desk research says runtime 1.4 serves no `/v1/embeddings`. |

## Decision

Chunks, embeddings and the citation path (document, page, paragraph, licence) live in pgvector, started by `docker compose --profile rag`. The search itself runs in PostgreSQL and returns top-k chunk ids and scores. The same PostgreSQL is registered in Zetaris as a JDBC datasource, so chunk metadata is read and joined with the hazard views through Zetaris, and every citation keeps a Zetaris `query_id`.

Agents never put `<=>` or `<->` in Zetaris SQL.

## Consequences

- This is the exception [ADR 0003](0003-zetaris-only-data-path.md) asks for: agents call pgvector directly for ranking only. Text and metadata still come through Zetaris. Mihir accepts or changes it.
- A migration that registers the datasource needs the pgvector password as a `${VAR}` placeholder (a new `PGVECTOR_PASSWORD` in `ingestion/.env`). Nothing was added to `zetaris/migrations/` for this yet.
- The datasource needs `host.docker.internal:15432` reachable from the Zetaris containers. It is on Docker Desktop for Windows. Linux and WSL are not tested.
- If a stricter reading of ADR 0003 wins, the fallback is one `CREATE DATASOURCE VIEW` per search with the vector inside it. It works, but it creates and drops a view on every question.

## Open questions

- Embeddings: which model, where it runs, and the vector size (Ayush, Urvashi).
- Search `:8888/redoc` for vector features while signed in (Urvashi, one minute).
- Whether the metadata join in Zetaris is worth the extra hop at demo scale (a few thousand chunks).
