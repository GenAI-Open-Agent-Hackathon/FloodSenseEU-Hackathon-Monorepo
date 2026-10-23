# 0003. Zetaris is the only data path for agents

- Status: Proposed
- Date: 2026-10-22
- Owner: Mihir

## Context

The agents explain risk with numbers that must trace to a query, a dataset, and a source. Each person runs Zetaris locally. Views that should last are migrations, not edits in the SQL Editor.

## Decision

Agents read data only through Zetaris. They do not call Copernicus, gauge, or weather APIs themselves. Ingestion scripts and `zetaris/migrations/` are how data is staged and registered. `python tasks.py zetaris-sync` is the one sync command. It is still a stub: it exits successfully and sends no SQL.

A claim that uses a number cites the Zetaris `query_id` on the evidence record in [contracts/](../../contracts/README.md).

## Consequences

- A new view arrives as a new migration plus a verify query, reviewed by Urvashi.
- Host-side sync reads `ingestion/.env` (`127.0.0.1`). Containers use `host.docker.internal` in `agents/.env`.
- pgvector is an optional Compose profile. This decision does not let agents query it directly. If chunks live there, the accepted path is still a Zetaris query, unless a later ADR says otherwise.

## Open questions

- Zetaris vector features in this edition, registering pgvector from the Zetaris containers, vector column mapping, and pushdown (Urvashi).
- Whether `host-gateway` reaches Zetaris on `:8888` when it is bound only to `127.0.0.1` under WSL (Urvashi, Ayush).
- Lightning SQL support for `IF NOT EXISTS`, `CREATE OR REPLACE`, and `DROP` on our object types (Urvashi).
- Where seed rows live. Zetaris cannot read files on a laptop (Saleeta).
- View column names. The contract fields are the gameplan's proposal until Urvashi and Saleeta check the real sources.
