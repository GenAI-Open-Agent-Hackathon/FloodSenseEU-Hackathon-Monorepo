# 0003. Zetaris is the only data path for agents

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

The agents explain risk with numbers that must trace to a query, a dataset, and a source. Each person runs Zetaris locally. Views that should last are migrations, not edits in the SQL Editor.

## Decision

Agents read data only through Zetaris. They do not call Copernicus, gauge, or weather APIs themselves. Ingestion scripts and `zetaris/migrations/` are how data is staged and registered. `python tasks.py zetaris-sync` is the one sync command. As of `v0.1.0` it applies pending migrations and verifies declared views.

A claim that uses a number cites the Zetaris `query_id` on the evidence record in [contracts/](../../contracts/README.md).

## Consequences

- A new view arrives as a new migration plus a verify query, reviewed by Mihir (Zetaris path owner since 2026-10-25). Urvashi remains on the team for Zetaris expertise.
- Host-side sync reads `ingestion/.env` (`127.0.0.1`). Containers use `host.docker.internal` in `agents/.env`.
- pgvector is an optional Compose profile. This decision does not let agents query it directly. If chunks live there, the accepted path is still a Zetaris query, unless a later ADR says otherwise.

## Open questions

- Zetaris vector features in this edition, registering pgvector from the Zetaris containers, vector column mapping, and pushdown (Urvashi).
- Whether `host-gateway` reaches Zetaris on `:8888` when it is bound only to `127.0.0.1` under WSL (Urvashi, Ayush).
- Lightning SQL on Zetaris 2.4.3.1: `IF NOT EXISTS` is not supported. `OR REPLACE` works for `SCHEMASTORE VIEW`. Recorded in `zetaris/README.md`.
- Where seed rows live. Zetaris cannot read files on a laptop (Saleeta).
- View column names. The contract fields are the gameplan's proposal until Urvashi and Saleeta check the real sources.
