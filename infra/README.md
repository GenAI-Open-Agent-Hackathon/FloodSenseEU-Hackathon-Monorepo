# Infra

Purpose: notes for how we run FloodSense locally and, later, how CI reaches a Zetaris. The runnable definition of the local app is [`compose.yaml`](../compose.yaml) at the repo root, not a second compose file in this folder.

Owner: Mihir.

## Isolation

Our app is its own Compose project (`name: floodsense-app`):

- Own network, `floodsense-app-net`.
- Own volumes, prefixed `floodsense-app_`.
- No `container_name` (a fixed name would collide with someone else's stack).
- Published ports: API `18000`, UI `15173`, pgvector `15432`, Redis `16379`.
- Zetaris stays on UI `:3000`, REST `:8888`, JDBC `:10000`. Nightshift stays on `:8088`.
- Containers reach those host services through `host.docker.internal` and the URLs in each person's `.env`.

`make up` and `make down` affect this project only. They do not start, stop, or modify Zetaris. Do not run `docker system prune` or `docker volume prune` on a machine that also hosts Zetaris.

Optional profiles:

```bash
docker compose --profile rag --profile cache up -d --build
```

`rag` adds pgvector. `cache` adds Redis. The engines sidecar (H-MEM and World Model, Ayush) is not in this skeleton.

## Not here yet

GitHub Actions (lint, test, secret guard, integration, release) land on a later feature branch. Do not add `.github/workflows` in the skeleton.
