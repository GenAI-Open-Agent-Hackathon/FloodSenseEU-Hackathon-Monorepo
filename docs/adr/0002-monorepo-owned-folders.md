# 0002. Monorepo with owned folders

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

Five peers change ingestion, Zetaris views, the agent graph, the API, and the UI in the same week. The gameplan already splits the tree into owned folders and asks for one review from outside the pair. GitHub Free enforces code owners only on a public repository, and the repo stays private until the security review.

## Decision

Keep one repository. [OWNERSHIP.md](../OWNERSHIP.md) says who reviews each path. Last matching row wins. `contracts/` and `.github/` are Mihir's, the same as the other architecture paths.

Work lands on short-lived branches through a pull request. Pairs share a branch. A review comes from outside the pair. Tags stay immutable, and Mihir creates them after a green `main`. This decision does not add an enforced CODEOWNERS file.

The Architect is one of the five peers, not a team lead. Scope changes are proposed by the area owner and agreed at stand-up.

## Consequences

- Contract changes are announced at the 14:00 check-in before they merge.
- A path can be edited by someone who does not own it, and the owner still reviews it.
- Branch protection while the repo is private is the team rule plus CI, not a GitHub ruleset.

## Open questions

- GitHub usernames are not filled in. The CODEOWNERS file waits until the team wants it and the repo is public.
- Whether the repository owner has GitHub Pro. The gameplan does not assume it.
