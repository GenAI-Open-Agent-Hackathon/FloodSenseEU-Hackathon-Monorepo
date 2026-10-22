.PHONY: up down up-all config check-env zetaris-sync test lint

# Pin the project. COMPOSE_PROJECT_NAME overrides compose.yaml `name:` and
# would attach these containers to another project, such as a local Zetaris
# stack. The -p flag wins over that variable.
COMPOSE = docker compose -p floodsense-app

# Our app only (project name floodsense-app). Does not start or stop Zetaris.
up: check-env
	$(COMPOSE) up -d --build

# pgvector (rag) and Redis (cache) as well. Still this project only.
up-all: check-env
	@test -f pgvector/.env || { echo "Missing pgvector/.env — cp pgvector/.env.example pgvector/.env"; exit 1; }
	$(COMPOSE) --profile rag --profile cache up -d --build

# Stops our project, including the optional rag and cache profiles.
# Does not delete volumes and does not touch any other compose project.
# Does not require the env files, so a missing pgvector/.env cannot trap a running stack.
down:
	$(COMPOSE) --profile rag --profile cache down

# Renders the resolved file. If a filled .env is present, secrets are printed.
# Do not log this on a machine that has real tokens. CI should use the examples.
config:
	$(COMPOSE) --profile rag --profile cache config

check-env:
	@test -f api/.env || { echo "Missing api/.env — cp api/.env.example api/.env"; exit 1; }
	@test -f agents/.env || { echo "Missing agents/.env — cp agents/.env.example agents/.env"; exit 1; }
	@test -f ui/.env || { echo "Missing ui/.env — cp ui/.env.example ui/.env"; exit 1; }

# Stub. Applies nothing until Urvashi implements scripts/zetaris_sync.py.
zetaris-sync:
	python3 scripts/zetaris_sync.py

test:
	python3 -m compileall -q api/app agents/floodsense_agents scripts
	cd api && python3 -m unittest discover -s tests -v
	cd agents && python3 -m unittest discover -s tests -v
	python3 -m unittest discover -s scripts/tests -v

# TODO: ruff, mypy, and the UI typecheck land with the CI feature branch.
lint:
	@echo "TODO: lint is not wired yet (ruff, mypy, ui tsc). CI is a later branch."
