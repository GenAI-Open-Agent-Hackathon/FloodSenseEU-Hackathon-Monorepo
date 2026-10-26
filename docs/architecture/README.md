# Architecture

Owner: Mihir. The diagrams are in [c4.md](c4.md): system context, containers, and the agent graph. A caption there says when a box is in `compose.yaml` today.

On `v0.2.0`, `build_graph()` in `agents/floodsense_agents/graph.py` compiles the graph (scope, Watchers, Investigator, Skeptic, Exposure, Playbook, Judge, HITL). It does not raise `NotImplementedError`. The API proxies runs, SSE, and approval. `GET /health` is the liveness check, not the only route. `zetaris-sync` applies migrations and verifies declared views.

The engines sidecar is in `compose.yaml`. The agents package does not call it. H-MEM and the World Model are not load-bearing on main until Ayush #15 and #16 merge. That split is drawn in [c4.md](c4.md).

Decisions are proposed in [../adr/](../adr/). The team accepts or changes them at stand-up.
