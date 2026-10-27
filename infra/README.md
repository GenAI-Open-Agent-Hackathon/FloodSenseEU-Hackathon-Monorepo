# Infra

Purpose: notes for how we run FloodSense locally and, later, how CI reaches a Zetaris. The runnable definition of the local app is [`compose.yaml`](../compose.yaml) at the repo root, not a second compose file in this folder.

Owner: Mihir.

## Isolation

Our app is its own Compose project (`name: floodsense-app`):

- Own network, `floodsense-app-net`.
- Own volumes, explicitly named `floodsense-app_checkpoints`, `floodsense-app_engines`, and `floodsense-app_pgdata`.
- No `container_name` (a fixed name would collide with someone else's stack).
- Published ports bind to `127.0.0.1`: API `18000`, UI `15173`, engines `8300`, pgvector `15432`, Redis `16379`. Redis has no password, and the pgvector password in the example is a shared placeholder, so neither port is on the LAN.
- Zetaris stays on UI `:3000`, REST `:8888`, JDBC `:10000`. Nightshift stays on `:8088`.
- Containers reach those host services through `host.docker.internal` (`extra_hosts: host-gateway` on the API and agents) and the URLs in `agents/.env`.

`python tasks.py up` and `python tasks.py down` pass `-p floodsense-app`, `--project-directory`, and `-f compose.yaml` (on Windows, `py tasks.py up`). An exported `COMPOSE_PROJECT_NAME` overrides the compose file's `name:` and would put these containers in that other project (verified with Compose 2.40: `COMPOSE_PROJECT_NAME=zetaris-stack` renamed the project and the checkpoint volume). `-p` wins. `COMPOSE_FILE` cannot select another file while the task script is the entry point. Do not start this stack with a bare `docker compose up`.

They do not start, stop, or modify Zetaris. Do not run `docker system prune` or `docker volume prune` on a machine that also hosts Zetaris.

`down` includes the rag and cache profiles so those containers stop too. Their env files are optional at parse time (`env_file.required: false`, Compose v2.24+). A missing `pgvector/.env` must not make `down` fail and push someone toward `docker system prune`. `up-all` still asks for `pgvector/.env` before starting the profile. There is no Makefile. PowerShell 5.x has no `&&`, and the task script does not use a shell.

Optional profiles:

```powershell
py tasks.py up-all
```

```bash
python3 tasks.py up-all
```

`rag` adds pgvector. `cache` adds Redis. The engines sidecar (H-MEM and World Model) starts with `python tasks.py up`. So does `pegel-poller` (no published port): it polls PEGELONLINE every `POLL_INTERVAL_S` (600) and `docker cp`s the CSV into `ZETARIS_CONTAINER` through the mounted Docker socket, so it is for development machines only. Inside the network the agents service uses `ENGINES_URL=http://engines:8300`. On the host the same service is `http://127.0.0.1:8300`. Compose sets `ENGINES_HOST=0.0.0.0` in the engines container so the agents service can connect, and publishes that port on loopback only.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pull requests to `main` and on pushes to `main`. `python tasks.py lint` rejects a tracked `.env` and runs gitleaks (default rules plus an `nvapi-` rule). On a pull request the scan is that pull request's commits (`base..head`). On a push to `main` it is the pushed range, or `HEAD` when the previous SHA is all zeros. `python tasks.py test` follows. A laptop with the binary on `PATH` scans the checked-out ref (`--log-opts=HEAD`), not every local branch. `.gitleaksignore` lists commit-specific fingerprints for deliberate fake fixtures in `scripts/tests/test_zetaris_sync.py` (`83abb6d` and, after the rebase onto main, `d2f3734`). It is not a path or rule allowlist.

The lint job uses `runs-on: ubuntu-latest` and Node 20. The homelab runner (`self-hosted`, `homelab`, 512Mi, no Docker assumed) is the commented line above that. One line moves the whole job. It does not call Zetaris or Nightshift, and it does not use Docker. The trade-off is [ADR 0008](../docs/adr/0008-ci-runner-github-hosted.md).

A second job, `engines`, installs Node 22.18 and runs `python tasks.py engines-test` (`npm test` and `npm run conformance`). Node 20 cannot run that sidecar. The gap stays on the lint job until that job moves off Node 20.

There is no pre-commit hook. `python tasks.py lint` is the local check. Gitleaks is optional on a laptop and required in CI (`FLOODSENSE_REQUIRE_GITLEAKS=1`).

Do not log `python tasks.py config` in CI. It prints resolved environment values.
