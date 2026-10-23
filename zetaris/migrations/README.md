# Zetaris migrations

Owner: Urvashi.

`020_live_gauges.sql` registers the PEGELONLINE Postgres tables and one REST example. Numbers below 020 are free for earlier sources (Saleeta's seed file is expected at `010_seed_sources.sql` and is not in this branch). Do not edit `020` after it has been applied. Add `021_...sql`.

Rules (see [../README.md](../README.md)):

- Numbered, append-only, idempotent.
- Do not edit a file after it has been merged. Add the next number.
- No passwords, tokens, or cloud keys in SQL. Use `${VAR}` placeholders.
- Put a `-- statement` line between statements so the sync tool can send them one at a time.

`python tasks.py zetaris-sync` is still a stub and will not apply these files until `scripts/zetaris_sync.py` is implemented. On Windows, `py tasks.py zetaris-sync`.
