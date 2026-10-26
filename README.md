# FloodSense EU

Europe-centric flood-risk agent for the Open Agent Hackathon 2026 (22–27 Oct, Track 02). It explains why an area is at risk, with cited, grounded claims. A Skeptic challenges the chain, an LLM-as-a-Judge scores it, and a human approves any outbound action.

The playbook is [docs/GAMEPLAN.md](docs/GAMEPLAN.md). Path ownership is [docs/OWNERSHIP.md](docs/OWNERSHIP.md). Diagrams are in [docs/architecture/c4.md](docs/architecture/c4.md). Proposed decisions are in [docs/adr/](docs/adr/).

Release notes are [CHANGELOG.md](CHANGELOG.md) and the GitHub Releases: [v0.0.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.0.0) (skeleton, `eacf34c`), [v0.1.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.1.0) (data slice, `7045fc5`), [v0.2.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.2.0) (live demo stack: agents graph, insurer desk, engines, fast lane, and parallel Zetaris), [v0.3.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.3.0) (live gauges and `hazard_now`), [v0.9.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.9.0) (H-MEM recall and write-on-approval, World Model bridge, short-term thread memory, sqlite hang fix), [v0.12.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.12.0) (semantic cache and labelled replay, [#17](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/17); `FF_SEMANTIC_CACHE` and `FF_CACHED_REPLAY` default off; rate limits are still a follow-up), [v0.13.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.13.0) (demo baseline: UI shell, audit fixes, Valencia seed path), and [v0.14.0](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.14.0) (RAG layer (c): corpus, `rag.chunks` and Zetaris JDBC, NIM ingest, `retrieve_docs`; `FF_RAG_DOCS` default off). Laptop Zetaris e2e for v0.3.0 is deferred to the morning of 26 Oct 2026. There is no `v0.4.0`–`v0.8.0` tag and no `v0.10.0` tag. `v0.11.0` is the retired name for layer (c) and is not a tag. The cache shipped as `v0.12.0`. There is no patch ladder between `v0.9.0` and `v0.14.0`. There is no wiki. Release notes live in [CHANGELOG.md](CHANGELOG.md) and GitHub Releases.

## Team

Five peers. The Architect is one role among them, not a team lead.

| Person | Role |
| --- | --- |
| Mihir | Architect: architecture, docs and ADRs, CI/CD, security review. Zetaris and data (takeover 2026-10-25). Judge with Zain. |
| Urvashi | Zetaris expertise. Remains on the team. |
| Saleeta | Secondary on ingestion prep and the demo. Citations and the slide deck. |
| Ayush | Nightshift, H-MEM, World Model, and the engines sidecar. |
| Zain | LangGraph, human-in-the-loop, the Judge with Mihir, then the UI. |

## Quick start

You need Python 3.10+ and Docker Desktop. You do not need Make, WSL, or Git Bash. Tasks live in `tasks.py` (stdlib only):

```text
python tasks.py <command>
py tasks.py <command>
```

`py` is the Windows launcher. `python` or `python3` is the same script. Run one command per line. PowerShell 5.x does not support `&&`.

Zetaris (UI `:3000`, REST `:8888/api/v1.0`, JDBC `:10000`) and Nightshift (`http://127.0.0.1:8088/v1`) are each person's own processes. This repository does not start them.

PowerShell 5.x or 7:

```powershell
py tasks.py init-env
py tasks.py up
Invoke-RestMethod http://127.0.0.1:18000/health
py tasks.py down
```

bash (macOS or Linux):

```bash
python3 tasks.py init-env
python3 tasks.py up
curl -s http://127.0.0.1:18000/health
python3 tasks.py down
```

`init-env` copies each missing `.env.example` to `.env` and does not overwrite a file that is already there. Fill `agents/.env` and `ingestion/.env` locally. In PowerShell, `curl` is an alias of `Invoke-WebRequest` and does not accept `-s`. Use `Invoke-RestMethod`, or `curl.exe` if you want the real curl.

`up` builds and starts the API (`127.0.0.1:18000`), the agent runtime (no host port), the engines sidecar (`127.0.0.1:8300`), and the UI (`127.0.0.1:15173`). Published ports bind to loopback. It refuses to start until `api/.env`, `agents/.env`, and `ui/.env` exist. Optional profiles:

```powershell
py tasks.py up-all
```

```bash
python3 tasks.py up-all
```

That adds pgvector on `127.0.0.1:15432` and Redis on `127.0.0.1:16379`. `init-env` also copies `pgvector/.env.example`. `down` stops this project only, including those profiles, even when `pgvector/.env` was never created. It does not remove volumes and it does not stop Zetaris.

Compose is always `docker compose -p floodsense-app` with this repo's `compose.yaml`. An exported `COMPOSE_PROJECT_NAME` or `COMPOSE_FILE` cannot point the task script at another Compose project. If you run `docker compose` yourself, pass the same `-p`.

`zetaris-sync` applies pending files in `zetaris/migrations/` and then verifies declared views. It reads `ingestion/.env` (`127.0.0.1`), not `agents/.env`. A cold laptop stages FILESTORE CSVs with `ingestion/prep/stage_local_zetaris.py` before migration 010. Details are in [zetaris/README.md](zetaris/README.md).

`test` compiles the Python packages and runs the unit tests with the current interpreter. Install the agents, API, contract, and dev requirements into a virtualenv first, then run `test` and `lint` with that interpreter. The engines tests need Node.js 22.18 or newer: `python tasks.py engines-test` (Windows: `py tasks.py engines-test`). With `ENGINES_URL` set, the agents call that sidecar: the World Model takes anomalies and hypotheses, and H-MEM recall plus write-on-approval run behind `FF_HMEM` (default off, so the graph keeps `NoMemory`). Short-term thread memory is `thread_id` on `POST /runs` and does not use the sidecar. Lane names are `meterless/fast` and `meterless/deep`. The one map to the model that answers today is the table at the top of [docs/architecture/c4.md](docs/architecture/c4.md). The API semantic cache and labelled replay (`v0.12.0`) sit behind `FF_SEMANTIC_CACHE` and `FF_CACHED_REPLAY`, both default off. Rate limits are still a follow-up.

PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r agents\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r api\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r contracts\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tasks.py test
cd ui
npm ci
cd ..
.\.venv\Scripts\python.exe tasks.py lint
```

bash:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r agents/requirements.txt
.venv/bin/python -m pip install -r api/requirements.txt
.venv/bin/python -m pip install -r contracts/requirements.txt
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python tasks.py test
cd ui
npm ci
cd ..
.venv/bin/python tasks.py lint
```

Calling the venv interpreter directly avoids PowerShell's script execution policy, which can block `Activate.ps1`. `lint` checks that no filled `.env` file is tracked, runs Ruff, and typechecks `ui/` and `contracts/`. If `gitleaks` is on `PATH`, `lint` runs it on the checked-out ref (`--log-opts=HEAD`), not on every local branch. CI sets `FLOODSENSE_GITLEAKS_LOG_OPTS` to the pull request's commits, or to the pushed range on `main`. If the binary is missing, `lint` prints one line and continues. One command per line. Do not join them with `&&`.

Containers call Zetaris and Nightshift at `host.docker.internal` (`agents/.env`). Host-side scripts use `127.0.0.1` (`ingestion/.env`, and the host-side copies in the root `.env`). The root file is not injected into containers. `host.docker.internal` is wired with `extra_hosts: host-gateway` so Linux and WSL Docker Engine can resolve it. Docker Desktop on Windows already resolves that name. A service bound only to `127.0.0.1` on the host may still be unreachable from a container; that check is Ayush and Urvashi's.

## Layout

| Path | Purpose | Owner |
| --- | --- | --- |
| `ingestion/` | Fetch and stage datasets, seed content | Mihir. Saleeta is secondary on prep and the demo |
| `zetaris/migrations/` | Numbered SQL, applied by `zetaris-sync` | Mihir |
| `agents/` | LangGraph graph, HITL interrupt, Judge, engines client, short-term thread memory | Ayush, Zain |
| `api/` | FastAPI. Proxies runs, SSE, and approval. `v0.12.0` adds the semantic cache and labelled replay, flags default off. `GET /health` as well | Zain, Ayush |
| `ui/` | Citizen page and insurer console (Vite, React, TypeScript). `v0.13.0` adds the shell nav and hash pages | Zain. Mihir landed the console |
| `engines/` | H-MEM and World Model sidecar | Ayush |
| `evals/` | Valencia 2024 and Ahr 2021 items. In v0.2.0, not its own increment tag | Saleeta, Zain, Mihir |
| `infra/` | How local compose stays off the Zetaris stack | Mihir |
| `contracts/` | JSON Schema for claims, citations, answers, approvals | Mihir |
| `tasks.py` | Cross-platform task runner (`up`, `down`, `zetaris-sync`, `engines-test`, `test`, `lint`) | Mihir |
| `.github/workflows/` | Lint, tests, secret scan, migration dry run, engines tests | Mihir |
| `docs/` | Gameplan, ownership, C4 diagrams, ADRs | Mihir |

## Branching

`main` is the integration branch. Further work lands on short-lived branches (`feat/<area>-<topic>`, `fix/…`, `chore/…`) through pull requests, with one review from outside the pair. Product tags on the 0.x line are `v0.MINOR.0` only: `v0.0.0`, `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.9.0` (memory), `v0.12.0` (semantic cache and labelled replay; flags default off), `v0.13.0` (demo baseline: UI shell, audit fixes, Valencia seed path), and `v0.14.0` (RAG layer (c); `FF_RAG_DOCS` default off). `v0.4.0` through `v0.8.0` are not tags. `v0.10.0` shipped inside `v0.2.0`. `v0.11.0` is the retired name for layer (c) and is not a tag. There is no patch ladder between `v0.9.0` and `v0.14.0`. The Monday freeze tag remains `v1.0.0-rc.1`. There is no `v0.x.y` fix tag. Candidates are `v1.0.0-rc.N`. Tags are not moved. See the gameplan for the increment list. `.github/workflows/ci.yml` runs on pull requests to `main` and on pushes to `main`. It does not create tags.

## Secrets

- Commit `.env.example` only. `.env` and `.env.*` are git-ignored.
- Zetaris keys and the Nightshift runtime token are created per person and stay in that person's env file.
- The NVIDIA chat key lives only in Nightshift's Providers tab. Do not put that chat key in an app env var, a workflow secret, a fixture, or Cursor's model settings. Document embeddings use `NVIDIA_NIM_API_KEY` in a gitignored env file. That key is not the Providers-tab chat key. See ADR 0009.
- Examples contain placeholders. SQL uses `${VAR}` placeholders, never literal keys.
- If a real secret is committed, rotate it. Removing the file is not enough.
- CI rejects a tracked `.env` file other than `.env.example`, and it fails if gitleaks finds an NVIDIA `nvapi-` key or another secret in that pull request's commits (on a push to `main`, in the pushed commits). See [docs/adr/0008-ci-runner-github-hosted.md](docs/adr/0008-ci-runner-github-hosted.md).
