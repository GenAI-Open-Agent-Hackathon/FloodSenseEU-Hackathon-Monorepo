# FloodSense EU

Europe-centric flood-risk agent for the Open Agent Hackathon 2026 (22–27 Oct, Track 02). It explains why an area is at risk, with cited, grounded claims. A Skeptic challenges the chain, an LLM-as-a-Judge scores it, and a human approves any outbound action.

The playbook is [docs/GAMEPLAN.md](docs/GAMEPLAN.md). Path ownership is [docs/OWNERSHIP.md](docs/OWNERSHIP.md).

## Team

Five peers. The Architect is one role among them, not a team lead.

| Person | Role |
| --- | --- |
| Mihir | Architect: architecture, docs and ADRs, CI/CD, security review. Judge with Zain. UI until Zain is free. |
| Urvashi | Zetaris: ingestion, migrations, vector-search research. |
| Saleeta | Ingestion with Urvashi, citation pipeline, slide deck and demo. |
| Ayush | Meterless Nightshift client, H-MEM, World Model, memory, embeddings, answer cache. |
| Zain | LangGraph agents, human-in-the-loop, LLM-as-a-Judge with Mihir, then the UI. |

## Quick start

Zetaris (UI `:3000`, REST `:8888/api/v1.0`, JDBC `:10000`) and Nightshift (`http://127.0.0.1:8088/v1`) are each person's own processes. This repository does not start them.

```bash
cp .env.example .env
cp api/.env.example api/.env
cp agents/.env.example agents/.env
cp ui/.env.example ui/.env
cp ingestion/.env.example ingestion/.env
# optional, only with --profile rag:
cp pgvector/.env.example pgvector/.env

# fill the copies locally, then:
make up
curl -s http://127.0.0.1:18000/health
make down
```

`make up` builds and starts the API (host port 18000), the agent runtime (no host port), and the UI (host port 15173). Optional profiles:

```bash
docker compose --profile rag --profile cache up -d --build
```

That adds pgvector on 15432 and Redis on 16379. `make down` stops this project only, including those profiles. It does not remove volumes and it does not stop Zetaris.

`make zetaris-sync` is a stub. It prints a TODO and applies no SQL. `make test` compiles the Python packages and runs the skeleton unit tests (install API deps first: `pip install -r api/requirements.txt`). `make lint` is a TODO until the CI branch.

Containers call Zetaris and Nightshift at `host.docker.internal`. Host-side scripts use `127.0.0.1`. Both URLs are configuration.

## Layout

| Path | Purpose | Owner |
| --- | --- | --- |
| `ingestion/` | Fetch and stage datasets, seed content | Urvashi, Saleeta |
| `zetaris/migrations/` | Numbered, append-only, idempotent SQL | Urvashi |
| `agents/` | LangGraph package: investigator, skeptic, judge, HITL placeholders | Ayush, Zain |
| `api/` | FastAPI. `/health` only | Zain, Ayush |
| `ui/` | Vite + React + TSX placeholder | Mihir, then Zain |
| `infra/` | How local compose stays off the Zetaris stack | Mihir |
| `docs/` | Gameplan, ownership, ADRs | Mihir |

## Branching

`main` is the integration branch. This skeleton is that base. Further work lands on short-lived branches (`feat/<area>-<topic>`, `fix/…`, `chore/…`) through pull requests, with one review from outside the pair. Release tags are `v0.x` (increments), `v0.x.y` (fixes), and `v1.0.0-rc.N` (candidates). Tags are not moved. See the gameplan for the increment list. GitHub Actions is a later feature branch, not part of this commit.

## Secrets

- Commit `.env.example` only. `.env` and `.env.*` are git-ignored.
- Zetaris keys and the Nightshift runtime token are created per person and stay in that person's env file.
- The NVIDIA provider key lives only in Nightshift's Providers tab. Do not put it in an app env var, a workflow secret, a fixture, or Cursor's model settings.
- Examples contain placeholders. SQL uses `${VAR}` placeholders, never literal keys.
- If a real secret is committed, rotate it. Removing the file is not enough.
