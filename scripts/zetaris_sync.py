"""Zetaris sync stub.

TODO (Urvashi): apply numbered, append-only SQL migrations in
zetaris/migrations/ through the documented Zetaris REST endpoint, record a
per-machine ledger at .zetaris-sync/ledger.json, and run verify queries.

See zetaris/README.md. This stub applies nothing.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    print("zetaris-sync: TODO — not implemented. No SQL was sent.")
    print("Planned: apply zetaris/migrations/NNN_*.sql in order (idempotent).")
    print("Planned ledger: .zetaris-sync/ledger.json (git-ignored, per machine).")
    if args:
        print("Arguments ignored by the stub:", " ".join(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
