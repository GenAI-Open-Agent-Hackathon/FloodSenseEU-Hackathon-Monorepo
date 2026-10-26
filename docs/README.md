# Docs

Owner: Mihir (architecture, ADRs, security review). The Architect is one role among five peers, not a team lead.

- [GAMEPLAN.md](GAMEPLAN.md) — how we ship FloodSense EU this week.
- [RELEASING.md](RELEASING.md) — changelog lines on each pull request, the 20:00 tag, and the GitHub Release.
- [OWNERSHIP.md](OWNERSHIP.md) — who reviews which paths. This is not an enforced CODEOWNERS file.
- [architecture/c4.md](architecture/c4.md) — system context, containers, and the agent graph.
- [superpowers/specs/2026-10-26-rag-layer-c-design.md](superpowers/specs/2026-10-26-rag-layer-c-design.md) — layer (c) tool RAG, shipped in `v0.14.0`. `FF_RAG_DOCS` stays off.
- [reviews/0001-skeleton-review.md](reviews/0001-skeleton-review.md) — review of the `v0.0.0` skeleton.

ADRs. `0001` is accepted. `0002` onward are proposed. The team accepts or changes them at stand-up.

- [adr/0001-record-architecture-decisions.md](adr/0001-record-architecture-decisions.md) — we record decisions as ADRs.
- [adr/0002-monorepo-owned-folders.md](adr/0002-monorepo-owned-folders.md) — one repo, owned paths, no enforced CODEOWNERS yet.
- [adr/0003-zetaris-only-data-path.md](adr/0003-zetaris-only-data-path.md) — agents read only through Zetaris.
- [adr/0004-nightshift-only-llm-calls.md](adr/0004-nightshift-only-llm-calls.md) — chat completions go through Nightshift on pinned lanes. Document embeddings are the ADR 0009 exception.
- [adr/0005-human-approval-before-outbound-action.md](adr/0005-human-approval-before-outbound-action.md) — a person approves every outbound action.
- [adr/0006-labelled-cache-and-replay.md](adr/0006-labelled-cache-and-replay.md) — `served_from` and `cached_at`.
- [adr/0007-json-schema-contracts.md](adr/0007-json-schema-contracts.md) — JSON Schema is the shared contract.
- [adr/0008-ci-runner-github-hosted.md](adr/0008-ci-runner-github-hosted.md) — CI runs on GitHub-hosted runners.
- [adr/0009-vector-search-next-to-zetaris.md](adr/0009-vector-search-next-to-zetaris.md) — rank in pgvector, hydrate text and licence through Zetaris. Embeddings are NVIDIA NIM, not Nightshift.

CI is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). The runner switch is the `runs-on` line in that file.
