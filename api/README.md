# API

Purpose: the FastAPI service the UI and the demo call. Planned surface: create a run, stream events (SSE), accept an approval, serve cached or replayed answers with a `cached at HH:MM` label, and rate-limit. This skeleton implements `GET /health` only.

Owner: Zain (runs, SSE, approval) and Ayush (cache and past runs). Mihir adds rate limits.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl -s http://127.0.0.1:8000/health
```

Inside compose the process listens on port 8000 and is published on host port 18000. Copy `.env.example` to `.env` before `make up`.

The NVIDIA provider key is not a variable for this service. It lives only in Nightshift's Providers tab.
