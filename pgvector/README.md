# pgvector (optional)

Purpose: local Postgres with the `vector` extension for citation chunks and embeddings (layer (c) citations). Started only with the compose `rag` profile. It is not required for the hackathon demo's layer (a) and (b) citations. `v0.14.0` is the layer (c) ship tag and is not cut in the design pull request. The design is [docs/superpowers/specs/2026-10-26-rag-layer-c-design.md](../docs/superpowers/specs/2026-10-26-rag-layer-c-design.md). `FF_RAG_DOCS` stays off. This folder does not yet hold a schema.

The embedding model is `nvidia/llama-nemotron-embed-1b-v2`, dimension 2048, from NVIDIA NIM `POST /v1/embeddings` (ADR 0009). Owner: Urvashi (store). Ayush owns the embedding client. JDBC hydration through Zetaris is required for a layer (c) citation: ranking stays in this Postgres, and text, licence, and locator are read through Zetaris so the citation keeps a `query_id`.

From the repo root, `python tasks.py init-env` (Windows: `py tasks.py init-env`) copies this example if `pgvector/.env` is missing. Then:

```powershell
py tasks.py up-all
```

```bash
python3 tasks.py up-all
```

`up-all` also starts Redis. API, agent, and UI env files must exist (the task script names any that are missing).

Host port `127.0.0.1:15432` (not published on the LAN). The password in `.env.example` is a local placeholder. Replace it in the git-ignored `.env`. `up-all` is the command that starts this profile. `python tasks.py down` still works if this file was never copied.

This database is part of the FloodSense compose project. It is not the Zetaris stack. Registering it as a Zetaris JDBC source is required for layer (c), not optional. The registration is specified in ADR 0009 and is not written in this pull request.
