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
| `/engines/` | Ayush | H-MEM and World Model sidecar. On main, in v0.2.0. Not load-bearing until #15 and #16. The agents package does not call it yet |
| `/agents/` | Ayush, Zain | Nightshift, graph, memory |
| `/agents/floodsense_agents/hitl.py` | Zain | Approval interrupt and checkpointer |
| `/agents/floodsense_agents/nodes/judge.py` | Zain, Mihir | LLM-as-a-Judge |
| `/api/` | Zain, Ayush | Runs, SSE, approval; cache is Ayush's |
| `/ui/` | Zain | Citizen page and insurer console. Zain owns the UI path. Mihir landed the console |
| `/pgvector/` | Urvashi | Stretch. Optional store for citation layer (c). Ayush on embeddings. Not load-bearing |
| `/evals/` | Saleeta, Zain, Mihir | In v0.2.0: Valencia 2024 and Ahr 2021. Not its own increment tag |
| `/demo/` | Saleeta | No folder yet. Deck, script, video |

`engines/` and `evals/` are on main, in v0.2.0. Live gauge views and `hazard_now` are in v0.3.0 (`/zetaris/`, `/ingestion/`). Laptop Zetaris e2e for that tag is deferred to the morning of 26 Oct 2026. The next tag after `v0.3.0` is `v0.9.0` once #15 and #16 are load-bearing, or `v1.0.0-rc.1` at the Monday 20:00 CET freeze. `v0.4.0` through `v0.8.0` and `v0.10.0` stay inside `v0.2.0`. Tags stay `v0.MINOR.0` only. Planned paths that still have no folder (`knowledge/`, `demo/`) follow the same owners when they appear. See [GAMEPLAN.md](GAMEPLAN.md).
