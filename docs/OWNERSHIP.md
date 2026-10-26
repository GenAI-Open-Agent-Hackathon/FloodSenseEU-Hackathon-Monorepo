# Ownership

This is the team's ownership table. It is not an enforced `.github/CODEOWNERS` file. GitHub Free only enforces code owners on public repositories, and that file can wait. Until then, "one review from outside the pair" is the team rule.

Ownership means: this person reviews changes on the path and keeps it working. It does not mean they are the only person who may edit it. Last matching row wins when two rows overlap, same as CODEOWNERS.

GitHub usernames are not filled in yet. Replace the names with real logins when the team adds a CODEOWNERS file.

| Path | Owners | Notes |
| --- | --- | --- |
| `*` | Mihir | Architecture, docs, CI/CD, security review |
| `/docs/` | Mihir | Gameplan, ADRs, later legal notes and release notes |
| `/infra/` | Mihir | Local runtime notes. The CI runner choice is ADR 0008 |
| `/compose.yaml` | Mihir | Our app only. Isolated from Zetaris |
| `/tasks.py` | Mihir | Task runner. `zetaris-sync` behaviour is Mihir's (takeover 2026-10-25) |
| `/contracts/` | Mihir | JSON Schema and the Python and TypeScript mirrors |
| `/.github/` | Mihir | Workflows |
| `/ingestion/` | Mihir, Saleeta | Mihir primary (takeover 2026-10-25), including live gauges. Saleeta secondary on prep and demo content |
| `/ingestion/feeds/` | Mihir | Live gauges. PEGELONLINE (WSV Rhine levels) is the gauge feed on main |
| `/zetaris/` | Mihir | Migrations, sync, views, including the live-gauge tables. Takeover 2026-10-25. Urvashi remains on the team for Zetaris expertise |
| `/scripts/zetaris_sync.py` | Mihir | The one sync command. Takeover 2026-10-25 |
| `/scripts/nightshift_check.py` | Ayush | Live check of the local Nightshift runtime |
| `/engines/` | Ayush | H-MEM and World Model sidecar. On main since v0.2.0. v0.9.0 calls it when `ENGINES_URL` is set: World Model on that URL, H-MEM recall and write-on-approval behind `FF_HMEM` (default off). The trust ledger stays on the sidecar (`GET /hmem/ledger`) |
| `/agents/` | Ayush, Zain | Nightshift, graph, memory |
| `/agents/floodsense_agents/hitl.py` | Zain | Approval interrupt and checkpointer |
| `/agents/floodsense_agents/nodes/judge.py` | Zain, Mihir | LLM-as-a-Judge |
| `/api/` | Zain, Ayush | Runs, SSE, approval. `v0.12.0` adds the semantic cache and labelled replay (`FF_SEMANTIC_CACHE`, `FF_CACHED_REPLAY`, both default off). Cache is Ayush's. Rate limits are Mihir's and are still a follow-up |
| `/ui/` | Zain | Citizen page and insurer console. `v0.13.0` adds the shell nav and hash pages ([#36](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/36)). Zain owns the UI path. Mihir landed the console |
| `/corpus/` | Urvashi, Saleeta, Mihir | Layer (c) manifest and redistributable documents. The ship tag is `v0.14.0`. The folder is not created yet |
| `/pgvector/` | Urvashi | `v0.14.0` document store for layer (c). Ayush on the embedding model. JDBC hydrate through Zetaris is required (ADR 0009). Not in `v0.13.0`. Not load-bearing while `FF_RAG_DOCS` is off |
| `/evals/` | Saleeta, Zain, Mihir | In v0.2.0: Valencia 2024 and Ahr 2021. Not its own increment tag |
| `/demo/` | Saleeta | No folder yet. Deck, script, video |

`engines/` and `evals/` are on main, in v0.2.0. Live gauge views and `hazard_now` are in v0.3.0 (`/zetaris/`, `/ingestion/`). Laptop Zetaris e2e for that tag is deferred to the morning of 26 Oct 2026. `v0.9.0` is memory: the agents call `engines/` when `ENGINES_URL` is set, and short-term thread memory lives in `/agents/`. `v0.12.0` is the semantic cache and labelled replay in `/api/` ([#17](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/17)). `FF_SEMANTIC_CACHE` and `FF_CACHED_REPLAY` are in the tree and default off. Rate limits are still a follow-up. `v0.13.0` is the demo baseline: the UI shell in `/ui/` ([#36](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/36)), the audit fixes ([#37](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/37)), the Zetaris sync `User-Agent` ([#30](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/30)), and the PR-review skill ([#35](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/35)). The [#39](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/39) `local/` gitignore commit is on this tag and omitted from the notes (`skip-changelog`). The Monday freeze tag remains `v1.0.0-rc.1`. `v0.4.0` through `v0.8.0` and `v0.10.0` stay inside `v0.2.0`. `v0.11.0` is the retired name for layer (c) and is not a tag. `v0.14.0` is the layer (c) ship tag and is not cut in the design pull request. It is not in `v0.13.0`. There is no `v0.4.0`–`v0.8.0` tag and no patch ladder between `v0.9.0` and `v0.13.0`. Tags stay `v0.MINOR.0` only. The wiki is disabled. Notes are [CHANGELOG.md](../CHANGELOG.md) and GitHub Releases. Planned paths that still have no folder (`knowledge/`, `demo/`, `corpus/`) follow the same owners when they appear. See [GAMEPLAN.md](GAMEPLAN.md).
