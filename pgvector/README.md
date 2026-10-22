# pgvector (optional)

Purpose: local Postgres with the `vector` extension for citation chunks and embeddings (layer (c) citations). Started only with the compose `rag` profile. It is not required for the hackathon demo's layer (a) and (b) citations.

Owner: Urvashi (store and Zetaris registration research). Ayush owns the embedding model choice.

```bash
cp .env.example .env
docker compose --profile rag up -d
```

Host port 15432. The password in `.env.example` is a local placeholder. Replace it in the git-ignored `.env`.

This database is part of the FloodSense compose project. It is not the Zetaris stack. Registering it as a Zetaris JDBC source is a later, optional check.
