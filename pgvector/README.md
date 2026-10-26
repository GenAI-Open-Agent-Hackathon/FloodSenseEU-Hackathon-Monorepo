# pgvector (optional)

Purpose: local Postgres with the `vector` extension for citation chunks and embeddings (layer (c) citations). Started only with the compose `rag` profile. It is not required for the hackathon demo's layer (a) and (b) citations. The store, its ingest, and `retrieve_docs` shipped in `v0.14.0`. The design is [docs/superpowers/specs/2026-10-26-rag-layer-c-design.md](../docs/superpowers/specs/2026-10-26-rag-layer-c-design.md). `FF_RAG_DOCS` stays off.

The embedding model is `nvidia/nemotron-3.5-embed-1b`, dimension 2048, from NVIDIA NIM `POST /v1/embeddings` (ADR 0009). Owner: Urvashi (store). Ayush owns the embedding client. JDBC hydration through Zetaris is required for a layer (c) citation: ranking stays in this Postgres, and text, licence, and locator are read through Zetaris so the citation keeps a `query_id`.

From the repo root, `python tasks.py init-env` (Windows: `py tasks.py init-env`) copies this example if `pgvector/.env` is missing. Then:

```powershell
py tasks.py up-all
```

```bash
python3 tasks.py up-all
```

`up-all` also starts Redis. API, agent, and UI env files must exist (the task script names any that are missing).

Host port `127.0.0.1:15432` (not published on the LAN). The password in `.env.example` is a local placeholder. Replace it in the git-ignored `.env`. `up-all` is the command that starts this profile. `python tasks.py down` still works if this file was never copied.

`pgvector/migrations/001_rag_chunks.sql` creates the empty `rag.chunks` table and the halfvec HNSW index. Apply it with `psql` against `127.0.0.1:15432`. The password stays in `pgvector/.env`. The migration does not insert rows. It does not call NIM. `scripts/rag_ingest.py` fills the table.

`pgvector/migrations/002_rag_embed_model_nemotron35.sql` moves the `embed_model` check to `nvidia/nemotron-3.5-embed-1b` (the old model is retired on NIM). Apply it after `001`, the same way.

Filling the table with `scripts/rag_ingest.py` needs an NVIDIA NIM key in `NVIDIA_NIM_API_KEY` and `PGVECTOR_DSN` in the environment of that command:

1. Sign in at [build.nvidia.com](https://build.nvidia.com) with a free NVIDIA account.
2. Open the `nvidia/nemotron-3.5-embed-1b` model page. (`nvidia/llama-nemotron-embed-1b-v2` is retired and answers HTTP 410.)
3. Choose **Get API Key**, then **Generate**. The key starts with `nvapi-`. The free tier's trial credits cover the corpus.
4. Put it in your gitignored `agents/.env` as `NVIDIA_NIM_API_KEY=`. Leave `NIM_EMBEDDINGS_URL` empty to use the default `https://integrate.api.nvidia.com/v1/embeddings`.
5. Do not commit it, paste it in chat, or put it in a fixture or screenshot. CI's gitleaks rule fails on an `nvapi-` string.

Zetaris migration `044` also needs `PGVECTOR_PASSWORD` in `ingestion/.env`, equal to `POSTGRES_PASSWORD` here. The model choice is in [ADR 0009](../docs/adr/0009-vector-search-next-to-zetaris.md).

This database is part of the FloodSense compose project. It is not the Zetaris stack. Registering it as a Zetaris JDBC source is required for layer (c), not optional. The registration is `zetaris/migrations/044_register_pgvector_rag_chunks.sql`. The password in that file stays `${PGVECTOR_PASSWORD}`.
