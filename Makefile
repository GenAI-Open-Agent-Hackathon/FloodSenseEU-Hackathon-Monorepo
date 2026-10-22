.PHONY: up down zetaris-sync test lint

# Our app only (project name floodsense-app). Does not start or stop Zetaris.
up:
	docker compose up -d --build

# Stops our project, including the optional rag and cache profiles.
# Does not delete volumes and does not touch any other compose project.
down:
	docker compose --profile rag --profile cache down

# Stub. Applies nothing until Urvashi implements scripts/zetaris_sync.py.
zetaris-sync:
	python3 scripts/zetaris_sync.py

test:
	python3 -m compileall -q api/app agents/floodsense_agents scripts
	cd api && python3 -m unittest discover -s tests -v
	cd agents && python3 -m unittest discover -s tests -v

# TODO: ruff, mypy, and the UI typecheck land with the CI feature branch.
lint:
	@echo "TODO: lint is not wired yet (ruff, mypy, ui tsc). CI is a later branch."
