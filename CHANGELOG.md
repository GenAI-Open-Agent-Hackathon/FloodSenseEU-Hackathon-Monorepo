# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Increment tags are `v0.MINOR.0`. A fix on an increment already tagged is `v0.MINOR.PATCH`. A release candidate is `v1.0.0-rc.N`. Tags are annotated and are not moved or deleted. The steps are in [docs/RELEASING.md](docs/RELEASING.md).

## [Unreleased]

### Added

- `scripts/nightshift_check.py`, a standard-library live check of the local Nightshift runtime. It reads the root `.env` (`127.0.0.1`), confirms that `/models` lists `MODEL_FAST` and `MODEL_DEEP` (an unlisted composed `meterless/` routing mode is a warning, not a failure), sends one JSON chat completion per tier with the agents client's request body (temperature 0.1, thinking off, JSON mode with the same 400 fallback; only the check caps the reply, at 256 tokens), and checks that each tier is answered by the model it wants (`EXPECT_MODEL_FAST` and `EXPECT_MODEL_DEEP`, both `nvidia/nemotron-3.5-super-vl-120b-a12b` by default; `any` accepts any model). A reply from another model is a warning, and so is both tiers answered by one model when they want different ones. `--probe` sends each candidate model id up to three times (`--probe-rounds`), shows which model answered, suggests `MODEL_FAST` and `MODEL_DEEP` values that reached the wanted model every time, and lists any routing details Nightshift returns beyond the model name. It skips local, fusion, cluster, embedding and media modes, so it never starts a local model load, and an upstream 5xx does not end a probe. The check also probes `/embeddings` when an embedding model is listed and prints a markdown summary for pull requests. It never prints the runtime token: the token is scrubbed from every server reply before any text is cut short, and a JSON error is shown in full, including Nightshift's own detail fields. Exit 0 when no required check fails (warnings included), 1 on a failed check, 2 on a config error. Run it with `python scripts/nightshift_check.py`. Tests in `scripts/tests/test_nightshift_check.py` use a fake runtime on `127.0.0.1`.

### Changed

- `MODEL_FAST` and `MODEL_DEEP` in `.env.example` and `agents/.env.example` are now `meterless/fast` and `meterless/deep`. Nightshift model ids are routing modes, so a request that named a model was answered by whichever lane Nightshift picked: the first live run got the 30B on both tiers, later runs the 120B. Nemotron 3.5 Super VL 120B A12B (`nvidia/nemotron-3.5-super-vl-120b-a12b`) now answers both tiers. Nightshift picks the faster lane, and Super VL is faster than Nemotron 3.5 Lightning 30B A3B (about 0.5 s against 2.6 s) as well as stronger; Lightning stays configured. NVIDIA deprecated the `nvidia/nemotron-3-super-120b-a12b` endpoint, which returns 502 "Function not found". The root `.env.example` lists the check's optional keys (`EXPECT_MODEL_FAST`, `EXPECT_MODEL_DEEP`, `MODEL_EMBED`). The gameplan and the C4 page say the same.

### Fixed

- The secret scan no longer walks every fetched branch. `gitleaks detect` with no `--log-opts` runs `git log --all`, and CI checks out with `fetch-depth: 0`, so fake fixtures on another branch failed unrelated pull requests. `python tasks.py lint` now passes `--log-opts`. CI sets `FLOODSENSE_GITLEAKS_LOG_OPTS` to `base..head` on a pull request, and to the pushed range on a push to `main` (`HEAD` when `github.event.before` is the all-zero SHA). With the variable unset, lint uses `--log-opts=HEAD` (the checked-out ref). Rules are unchanged.
- `.gitleaksignore` records two fingerprints from commit `83abb6d` in `scripts/tests/test_zetaris_sync.py`: the fake local-server `API_KEY` used by `test_applies_in_order_one_statement_per_call_with_documented_headers` (`generic-api-key`), and the fake AWS key inside `test_lint_flags_literal_secrets_but_not_placeholders` (`aws-access-token`). Each entry is that commit only. There is no path or rule allowlist.

## [0.0.0] - 2026-10-23

Skeleton and guardrails on `eacf34c`. The product described in the gameplan (live answers, ingestion, human approval, the insurer console) is not in this tag.

### Added

- Repository skeleton: README, gameplan, path ownership, and the folders `ingestion/`, `zetaris/migrations/`, `agents/`, `api/`, `ui/`, `infra/`, `pgvector/`, `contracts/`, `docs/`, and `scripts/`. The skeleton review is `docs/reviews/0001-skeleton-review.md`.
- `compose.yaml` for this application only, Compose project `floodsense-app`. It does not start Zetaris. `python tasks.py up` builds the API (published on `127.0.0.1:18000`), the agent runtime (no host port), and the UI (`127.0.0.1:15173`). `up-all` also starts optional pgvector (`127.0.0.1:15432`, profile `rag`) and Redis (`127.0.0.1:16379`, profile `cache`). `tasks.py` always passes `-p floodsense-app`, `--project-directory`, and `-f compose.yaml`, so `COMPOSE_PROJECT_NAME` and `COMPOSE_FILE` cannot point the script at another project. `up` refuses to start until `api/.env`, `agents/.env`, and `ui/.env` exist. `down` stops this project only, keeps volumes, and does not need `pgvector/.env`.
- `tasks.py`, a standard-library task runner: `init-env`, `check-env`, `up`, `up-all`, `down`, `config`, `zetaris-sync`, `test`, and `lint`. `init-env` copies each missing `.env.example` to `.env` and does not overwrite. There is no Makefile.
- Placeholders. The API implements `GET /health` only. `python -m floodsense_agents` serves a JSON health check on port 8100, and `build_graph()` raises `NotImplementedError`. The UI is a Vite, React, and TypeScript placeholder and does not call the API. `scripts/zetaris_sync.py` prints a TODO, exits 0, and applies no SQL. `zetaris/migrations/` has no SQL files yet. `agents/`, `api/`, and `ui/` do not import `contracts/`.
- Env examples that are safe to commit. Filled `.env` files are gitignored. Host examples use `127.0.0.1`. The agent container example uses `host.docker.internal`.
- Shared contracts in `contracts/schemas/floodsense.schema.json` (JSON Schema draft 2020-12) for `claim`, `citation`, `evidence`, `answer`, `playbook_action`, `approval`, and `judge`. Pydantic and TypeScript are hand-checked mirrors, not generated code. Files in `contracts/examples/` are fixtures, not measurements. `python tasks.py test` validates those examples against the schema and the Pydantic models. Direct test dependencies are pinned to pydantic 2.14.1 and jsonschema 4.26.0. Wire names are snake_case.
- `python tasks.py lint` rejects a tracked `.env` other than an example, runs Ruff, and typechecks `ui/` and `contracts/`. Gitleaks runs when the binary is on `PATH`.
- GitHub Actions workflow `.github/workflows/ci.yml` on pull requests to `main` and on pushes to `main`. The job uses `ubuntu-latest`, installs gitleaks 8.30.1 from the release archive after a checksum check, sets up Python 3.12 and Node 20, then runs `python tasks.py lint` and `python tasks.py test`. `FLOODSENSE_REQUIRE_GITLEAKS=1` fails the job when the scanner is missing. The workflow does not use Docker and does not call Zetaris or Nightshift. There is no pre-commit hook.
- C4 system context, container, and agent diagrams in `docs/architecture/c4.md` (Mermaid). A box is the gameplan unless the caption says that service is in `compose.yaml` today.
- ADR 0001 (Accepted): decisions are recorded in `docs/adr/`. ADRs 0002–0008 are Proposed, not accepted: one repository with owned folders, Zetaris as the only data path for agents, Nightshift as the only path for model calls, human approval before any outbound action, labelled cache and replay, JSON Schema as the shared contract, and GitHub-hosted CI.

### Security

- `.gitleaks.toml` keeps the default gitleaks rules and adds an `nvapi-` rule. CI fails when the scanner matches, and when a filled `.env` is tracked.
- The API, UI, pgvector, and Redis ports bind to `127.0.0.1`. Redis has no password. The pgvector example password is a local placeholder.
- Examples contain placeholders, not tokens. The NVIDIA provider key is not an application variable.

[Unreleased]: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/compare/v0.0.0...HEAD
[0.0.0]: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.0.0
