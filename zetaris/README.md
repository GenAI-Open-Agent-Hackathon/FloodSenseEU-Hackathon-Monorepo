# Zetaris

Purpose: the SQL that defines our Zetaris objects (Lightning sources, tables, and SCHEMASTORE views), applied the same way on every laptop.

Owner: Mihir (takeover 2026-10-25). He is the first contact for Zetaris sync and migrations. Saleeta remains secondary on ingestion prep and the demo.

## Migrations

Files in [`migrations/`](migrations/) are:

- **Numbered.** `001_short_name.sql`, `002_short_name.sql`, and so on. The sync tool applies them in sorted order.
- **Append-only.** A file that has been merged is never edited. A change is a new file (for example `021_...`). The tool will store a SHA-256 per applied file and stop if an applied file changed.
- **Idempotent.** Already-applied files are skipped via a per-machine ledger. Tested on Zetaris 2.4.3.1 (24 Oct 2026): `IF NOT EXISTS` and `IF EXISTS` are not supported anywhere (databases, REST tables, containers, views, drops: all parse errors), and `OR REPLACE` works only for `SCHEMASTORE VIEW`. So write `CREATE OR REPLACE SCHEMASTORE VIEW` for every view and plain `CREATE` for everything else. Re-creating an existing database, REST table, container or view answers `A <kind> named "<name>" already exists`, and the tool skips that statement and counts it in the ledger. Changing a REST table or container means a new numbered migration (drop, then create), never an edit. After a successful apply, including those skips and a run that had nothing pending, the tool verifies every declared view whose migration is in the ledger before it exits 0.
- **Free of secrets.** Keys appear only as `${VAR}` placeholders, filled from the person's own `ingestion/.env` at run time. The tool must not print rendered SQL.

One statement per REST request. Split a file on a line that is exactly `-- statement`. The only documented call is `POST {ZETARIS_REST_URL}/sql-editor/sqls/run` with `Authorization: Bearer`, `X-Org-ID`, and a fresh `X-Request-ID`.

Seed views (`floodsense_seed.*`) share the schemas of the live views so the agent pair can build before live sources are ready. Agents switch with `FF_LIVE_DATA`.

## Sync command

```powershell
py tasks.py zetaris-sync
```

```bash
python3 tasks.py zetaris-sync
```

That runs `scripts/zetaris_sync.py` on the host with the current interpreter. There is no Makefile.

With no arguments the script applies the pending migrations and then verifies declared views. A run that prints `nothing to apply`, and a statement skipped because it already exists, still go through that verify. Exit 0 means the checks passed. Other forms, run directly:

```text
python scripts/zetaris_sync.py sync --dry-run   parse, lint, check numbering; sends nothing (for CI)
python scripts/zetaris_sync.py status           applied, pending, changed; sends nothing
python scripts/zetaris_sync.py verify           DESCRIBE and COUNT each declared view; read-only
```

Applied files are recorded in `.zetaris-sync/ledger.json` (git-ignored, one per machine) with a SHA-256 of the file with LF line endings. If an applied file changed, the tool stops and asks for a new numbered file. A statement that fails with "already exists" is skipped and counted in the ledger, so a half-applied file can be re-run. Lint rejects literal secrets and bad file names.

`verify` reads the `-- view:`, `-- columns:` and `-- min_rows:` header lines of each applied migration and checks the live view's column names, types and row count. Its output has no timestamps or counts, so two machines in sync print identical text. Views whose migration is not applied are listed as SKIP. `contracts/views.yaml` is the reference for the column lists, and a unit test keeps the headers, the seed copies and the contract in step.

**TODO:** `reset` prints "not implemented yet" and sends nothing. Lightning SQL has no `DROP SCHEMASTORE CONTAINER`, so a full reset needs the Zetaris API or UI to remove containers.

Each person creates their own Zetaris API key in their own UI and stores it in `ingestion/.env` (host URL `127.0.0.1`). Do not point this command at `agents/.env`: that file is for containers and uses `host.docker.internal`, which usually does not resolve on the host. The root `.env` is not injected into containers. The sync command reads `ingestion/.env`, not the root file and not `agents/.env`. Nobody shares keys.

This folder does not start Zetaris. Zetaris is a separate Docker Compose project on each machine (UI `:3000`, REST `:8888/api/v1.0`, JDBC `:10000`).
