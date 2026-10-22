# Zetaris

Purpose: the SQL that defines our Zetaris objects (Lightning sources, tables, and SCHEMASTORE views), applied the same way on every laptop.

Owner: Urvashi. She is the first contact for any Zetaris issue during the hackathon. Saleeta adds seed views and provenance rows with her.

## Migrations

Files in [`migrations/`](migrations/) are:

- **Numbered.** `001_short_name.sql`, `002_short_name.sql`, and so on. The sync tool applies them in sorted order.
- **Append-only.** A file that has been merged is never edited. A change is a new file (for example `021_...`). The tool will store a SHA-256 per applied file and stop if an applied file changed.
- **Idempotent.** Already-applied files are skipped via a per-machine ledger. Where Lightning SQL supports `IF NOT EXISTS` or `OR REPLACE`, use it. That support is not verified yet (Urvashi, Day 1). If Zetaris answers that an object already exists, the tool should run the matching verify query instead of failing.
- **Free of secrets.** Keys appear only as `${VAR}` placeholders, filled from the person's own `.env` at run time. The tool must not print rendered SQL.

One statement per REST request. Split a file on a line that is exactly `-- statement`. The only documented call is `POST {ZETARIS_REST_URL}/sql-editor/sqls/run` with `Authorization: Bearer`, `X-Org-ID`, and a fresh `X-Request-ID`.

Seed views (`floodsense_seed.*`) share the schemas of the live views so the agent pair can build before live sources are ready. Agents switch with `FF_LIVE_DATA`.

## Sync command

```bash
make zetaris-sync
```

That runs `python3 scripts/zetaris_sync.py`.

**TODO:** the script is a stub. It prints a message and applies nothing. Urvashi implements the ledger (`.zetaris-sync/ledger.json`, git-ignored, one per machine), the dry run, and the verify step. Planned siblings, not in this skeleton: `make zetaris-status`, `make verify`, `make zetaris-reset`.

Each person creates their own Zetaris API key in their own UI and stores it in `.env`. Nobody shares keys.

This folder does not start Zetaris. Zetaris is a separate Docker Compose project on each machine (UI `:3000`, REST `:8888/api/v1.0`, JDBC `:10000`).
