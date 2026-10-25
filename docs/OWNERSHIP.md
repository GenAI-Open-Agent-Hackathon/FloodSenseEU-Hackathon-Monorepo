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
| `/ingestion/` | Mihir, Saleeta | Mihir primary (takeover 2026-10-25). Saleeta secondary on prep and demo content |
| `/zetaris/` | Mihir | Migrations, sync, views. Takeover 2026-10-25. Urvashi remains on the team for Zetaris expertise |
| `/scripts/zetaris_sync.py` | Mihir | The one sync command. Takeover 2026-10-25 |
| `/scripts/nightshift_check.py` | Ayush | Live check of the local Nightshift runtime |
| `/engines/` | Ayush | H-MEM and World Model sidecar. On main. The agents package does not call it yet |
| `/agents/` | Ayush, Zain | Nightshift, graph, memory |
| `/agents/floodsense_agents/hitl.py` | Zain | Approval interrupt and checkpointer |
| `/agents/floodsense_agents/nodes/judge.py` | Zain, Mihir | LLM-as-a-Judge |
| `/api/` | Zain, Ayush | Runs, SSE, approval; cache is Ayush's |
| `/ui/` | Zain, Mihir | Citizen page and insurer console are on main. Zain owns the path. Mihir landed the console |
| `/pgvector/` | Urvashi | Optional citation store. Ayush on embeddings |
| `/evals/` | Saleeta, Zain, Mihir | In v0.2.0: Valencia 2024 and Ahr 2021. Not its own increment tag |
| `/demo/` | Saleeta | No folder yet. Deck, script, video |

`engines/` and `evals/` are on main, in v0.2.0. Planned paths that still have no folder (`knowledge/`, `demo/`) follow the same owners when they appear. See [GAMEPLAN.md](GAMEPLAN.md).
