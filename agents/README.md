# Agents

Purpose: the LangGraph runtime. Planned graph: Watchers → Investigator → Skeptic → Exposure → Playbook → Judge → human-in-the-loop interrupt. Agents read data only through Zetaris and call models only through Meterless Nightshift.

Owner: Ayush (Nightshift client, H-MEM, World Model, memory, embeddings) and Zain (graph, HITL, Judge with Mihir).

This skeleton is placeholders. `python -m floodsense_agents` serves a tiny JSON health check on port 8100 so compose has a process to run. It does not call Nightshift or Zetaris. `build_graph()` raises `NotImplementedError`.

From the repo root, `python tasks.py init-env` copies `.env.example` to `.env` here when it is missing (Windows: `py tasks.py init-env`). Do that before `python tasks.py up`. From inside the container, Zetaris and Nightshift are reached at `host.docker.internal`. Host-side sync uses `ingestion/.env` and `127.0.0.1` instead. Checkpoints for a later SqliteSaver mount at `/data/checkpoints`. The image installs `requirements.txt` (comments only, until the LangGraph dependencies land).

In compose, the agents service reaches the engines sidecar at `ENGINES_URL=http://engines:8300`. On the host that URL is `http://127.0.0.1:8300`. `compose.yaml` sets the compose value.

The NVIDIA provider key is not a variable in `.env`. It lives only in Nightshift's Providers tab. Calls send `Authorization: Bearer <METERLESS_RUNTIME_TOKEN>`, `meterless-app`, and `meterless-scope: user`.

Routing modes (not wired yet). The app sends these ids. Nightshift picks the model. The map to the model that answers today is the table at the top of `docs/architecture/c4.md`.

- Fast: `meterless/fast`
- Deep: `meterless/deep`
