# pgvector (optional)

Purpose: local Postgres with the `vector` extension for citation chunks and embeddings (layer (c) citations). Started only with the compose `rag` profile. It is not required for the hackathon demo's layer (a) and (b) citations.

Owner: Urvashi (store and Zetaris registration research). Ayush owns the embedding model choice.

From the repo root, `python tasks.py init-env` (Windows: `py tasks.py init-env`) copies this example if `pgvector/.env` is missing. Then:

```powershell
py tasks.py up-all
```

```bash
python3 tasks.py up-all
```

`up-all` also starts Redis. API, agent, and UI env files must exist (the task script names any that are missing).

Host port `127.0.0.1:15432` (not published on the LAN). The password in `.env.example` is a local placeholder. Replace it in the git-ignored `.env`. `up-all` is the command that starts this profile. `python tasks.py down` still works if this file was never copied.

This database is part of the FloodSense compose project. It is not the Zetaris stack. `python tasks.py up-db` starts only this service. The PEGELONLINE poller creates schema `live` in this database. Registering it from Zetaris is `zetaris/migrations/020_live_gauges.sql` (untested on a live Zetaris). See [ingestion/live/README.md](../ingestion/live/README.md).
