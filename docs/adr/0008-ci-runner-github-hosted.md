# 0008. CI runs on GitHub-hosted runners

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

Pull requests need a check that fails on a tracked `.env`, on an NVIDIA `nvapi-` key, and on a failing test or lint. A self-hosted runner is registered for this repository with labels `self-hosted` and `homelab`. The task brief describes it as a plain container in a local Kubernetes cluster with 512Mi of memory, without a known Python or Node install, and likely without Docker. This ADR does not verify that the runner is online or that those limits still hold.

The checks in v0.0.0 do not call Zetaris or Nightshift. They do not need the homelab network.

## Decision

`.github/workflows/ci.yml` runs on pull requests to `main` and on pushes to `main`. The job uses `runs-on: ubuntu-latest`.

The switch is that one line. The homelab alternative is the commented line directly above it:

```yaml
runs-on: [self-hosted, homelab]
```

The job installs its own tools. It does not use Docker.

- Tracked env files: `python tasks.py lint` rejects any tracked path named `.env` or `.env.*`, except `.env.example` and `*.env.example`. A file full of placeholders would not look like a secret, so this check is separate from the scanner.
- Secrets: [gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1, with the default rules plus an `nvapi-` rule. The workflow verifies the upstream checksum and puts the binary on `PATH`. `FLOODSENSE_REQUIRE_GITLEAKS=1` makes a missing binary fail the job. Locally, `lint` runs gitleaks when the binary is on `PATH` and otherwise prints one line. `gitleaks detect` with an empty `--log-opts` runs `git log --all`. Checkout uses `fetch-depth: 0`, so that default would scan every fetched branch. `python tasks.py lint` always passes `--log-opts`. CI sets `FLOODSENSE_GITLEAKS_LOG_OPTS` to `base..head` on a pull request, and to the pushed range on a push to `main` (`HEAD` when `github.event.before` is the all-zero SHA). With the variable unset, lint uses `--log-opts=HEAD`, the checked-out ref only. Rules are unchanged. `.gitleaksignore` lists individual finding fingerprints (`commit:file:rule:line`) for two deliberate fake fixtures in `scripts/tests/test_zetaris_sync.py` on `feat/zetaris-data-sync` (commit `83abb6d`): the fake local-server key used by `test_applies_in_order_one_statement_per_call_with_documented_headers`, and the fake AWS key inside `test_lint_flags_literal_secrets_but_not_placeholders`. A fingerprint matches that commit only. The file is not a path or rule allowlist.
- Tests and lint: `python tasks.py test` and `python tasks.py lint` (Ruff, then `tsc` for `ui/` and `contracts/`).

We did not use `gitleaks/gitleaks-action`. Its README says organization accounts need `GITLEAKS_LICENSE`, and this repository is under an organization. The action is also unnecessary: the binary is the same scanner and does not need Docker.

There is no pre-commit hook. `python tasks.py lint` is the local check. Adding the pre-commit framework for one optional scanner was more tooling than this increment needs.

## Consequences

- A green check does not mean the homelab runner executed the job.
- A later job that must reach a laptop's Zetaris can flip the one line, after the image has enough memory and the tools the steps call (`bash`, `curl`, `tar`, and a runner that can execute the Node 24 actions).
- Action versions are floating major tags (`actions/checkout@v7` and the setup actions). Pinning those to commit SHAs belongs in the Tuesday security review, not in this increment.
- `python tasks.py config` is not a CI step. It prints resolved environment values.

## Open questions

- Whether the homelab runner is online, and whether its agent is new enough for Node 24 actions (v2.327.1 or newer). Not checked from this environment.
- Whether 512Mi can complete `npm ci` plus the test install. Not measured.
- Whether that container image contains `bash`, `curl`, and `tar`. Not inspected.
