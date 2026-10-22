# pgvector (optional)

Purpose: local Postgres with the `vector` extension for citation chunks and embeddings (layer (c) citations). Started only with the compose `rag` profile. It is not required for the hackathon demo's layer (a) and (b) citations.

Owner: Urvashi (store and Zetaris registration research). Ayush owns the embedding model choice.

From the repo root:

```bash
cp pgvector/.env.example pgvector/.env
make up-all
```

`make up-all` also starts Redis. API, agent, and UI env files must exist (`make` will say so).

Host port `127.0.0.1:15432` (not published on the LAN). The password in `.env.example` is a local placeholder. Replace it in the git-ignored `.env`. `make up-all` is the command that starts this profile. `make down` still works if this file was never copied.

This database is part of the FloodSense compose project. It is not the Zetaris stack. Registering it as a Zetaris JDBC source is a later, optional check.
