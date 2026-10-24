"""Apply the numbered SQL migrations in zetaris/migrations/ to a local Zetaris.

    python scripts/zetaris_sync.py                 apply pending migrations
    python scripts/zetaris_sync.py sync --dry-run  parse and lint, send nothing
    python scripts/zetaris_sync.py status          applied, pending, changed; send nothing
    python scripts/zetaris_sync.py verify          check each declared view against your Zetaris

A migration that creates a view declares what must be true of it in header comments:
"-- view: floodsense.discharge_daily", "-- columns: point_id string, date date" and
"-- min_rows: 8". verify runs DESCRIBE and a row count for each and prints OK or FAIL lines.

Sends one statement per call to POST {ZETARIS_REST_URL}/sql-editor/sqls/run,
the REST call the Zetaris setup guide documents, using the key in
ingestion/.env (127.0.0.1, not agents/.env). Files are split on a line that is
exactly "-- statement". ${VAR} placeholders are filled from the environment at
run time. Rendered SQL and secret values are never printed. What was applied is
recorded in .zetaris-sync/ledger.json (git-ignored, one per machine).

reset is not implemented yet. See zetaris/README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MIGRATIONS = ROOT / "zetaris" / "migrations"
DEFAULT_LEDGER = ROOT / ".zetaris-sync" / "ledger.json"
DEFAULT_ENV_FILE = ROOT / "ingestion" / ".env"
DEFAULT_REST_URL = "http://127.0.0.1:8888/api/v1.0"

STATEMENT_MARKER = "-- statement"
FILE_NAME = re.compile(r"^(\d{3})_[a-z0-9][a-z0-9_]*\.sql$")
PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
ALREADY_EXISTS = re.compile(r"already exists", re.IGNORECASE)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"nvapi-[A-Za-z0-9_-]{10,}"),
    re.compile(
        r"(?i)(?:secret|password|passwd|token|api[_-]?key|access[_-]?key)\w*"
        r"\W{1,4}['\"](?!\$\{|https?://)[^'\"\s]{6,}['\"]"
    ),
)
LEDGER_VERSION = 1
VIEW_HEADER = re.compile(r"^--\s*view:\s*(\S+)\s*$")
COLUMNS_HEADER = re.compile(r"^--\s*columns:\s*(.+?)\s*$")
MIN_ROWS_HEADER = re.compile(r"^--\s*min_rows:\s*(\d+)\s*$")
VIEW_NAME = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class SyncError(Exception):
    """A problem to report to the user. The message never contains secrets."""


class ZetarisError(Exception):
    """The REST call failed. The message may echo server text; redact before printing."""


@dataclass(frozen=True)
class ViewSpec:
    name: str
    columns: tuple[tuple[str, str], ...]
    min_rows: int | None


@dataclass(frozen=True)
class Migration:
    name: str
    number: int
    sha256: str
    statements: tuple[str, ...]
    placeholders: tuple[str, ...]
    views: tuple[ViewSpec, ...] = ()


def split_statements(text: str) -> list[str]:
    chunks: list[list[str]] = [[]]
    for line in text.splitlines():
        if line.rstrip() == STATEMENT_MARKER:
            chunks.append([])
        else:
            chunks[-1].append(line)
    statements = []
    for lines in chunks:
        if any(ln.strip() and not ln.strip().startswith("--") for ln in lines):
            statements.append("\n".join(lines).strip().rstrip(";").rstrip())
    return statements


def parse_view_specs(text: str) -> list[ViewSpec]:
    """Read the '-- view:', '-- columns:' and '-- min_rows:' header comments of a migration."""
    specs: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if match := VIEW_HEADER.match(line):
            specs.append({"name": match.group(1), "columns": (), "min_rows": None})
        elif specs and (match := COLUMNS_HEADER.match(line)):
            pairs = [part.split() for part in match.group(1).split(",")]
            specs[-1]["columns"] = tuple((p[0].lower(), p[1].lower()) for p in pairs if len(p) == 2)
        elif specs and (match := MIN_ROWS_HEADER.match(line)):
            specs[-1]["min_rows"] = int(match.group(1))
    return [ViewSpec(s["name"], s["columns"], s["min_rows"]) for s in specs]


def file_sha256(data: bytes) -> str:
    # Line endings differ between Windows and Linux checkouts. Hash the LF form
    # so the same file gives the same digest on every machine.
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def discover(directory: Path) -> tuple[list[Migration], list[str]]:
    migrations: list[Migration] = []
    problems: list[str] = []
    seen: dict[int, str] = {}
    for path in sorted(directory.glob("*.sql")):
        match = FILE_NAME.match(path.name)
        if not match:
            problems.append(f"{path.name}: name must look like 001_short_name.sql")
            continue
        number = int(match.group(1))
        if number in seen:
            problems.append(f"{path.name}: number {number:03d} is also used by {seen[number]}")
            continue
        seen[number] = path.name
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{path.name}: not valid UTF-8")
            continue
        statements = split_statements(text)
        if not statements:
            problems.append(f"{path.name}: no statements found")
            continue
        found = sorted({m for sql in statements for m in PLACEHOLDER.findall(sql)})
        migrations.append(
            Migration(
                path.name,
                number,
                file_sha256(data),
                tuple(statements),
                tuple(found),
                tuple(parse_view_specs(text)),
            )
        )
    migrations.sort(key=lambda m: m.name)
    return migrations, problems


def lint(migrations: list[Migration]) -> list[str]:
    problems = []
    for migration in migrations:
        for spec in migration.views:
            if not VIEW_NAME.match(spec.name):
                problems.append(f"{migration.name}: view name '{spec.name}' must be container.view")
            elif not spec.columns or spec.min_rows is None:
                problems.append(
                    f"{migration.name}: view {spec.name} needs '-- columns:' and '-- min_rows:' lines"
                )
        for index, sql in enumerate(migration.statements, 1):
            if any(pattern.search(sql) for pattern in SECRET_PATTERNS):
                problems.append(
                    f"{migration.name}: statement {index} looks like it holds a literal "
                    "secret. Use a ${VAR} placeholder."
                )
    return problems


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def render(sql: str, env: dict[str, str]) -> str:
    return PLACEHOLDER.sub(lambda m: env[m.group(1)], sql)


def redact(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def preview(sql: str) -> str:
    """Leading keywords only: enough to see progress without echoing SQL."""
    lines = [ln for ln in sql.splitlines() if ln.strip() and not ln.strip().startswith("--")]
    return " ".join(lines[0].split()[:6])[:70] if lines else ""


class Client:
    def __init__(self, base_url: str, org_id: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self._api_key = api_key

    def run(self, sql: str, limit: int = 100) -> list:
        body = json.dumps(
            {"queryId": str(uuid.uuid4()), "sql": sql, "source": "SqlEditor", "limit": limit}
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/sql-editor/sqls/run",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "X-Org-ID": self.org_id,
                "X-Request-ID": str(uuid.uuid4()),
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=600) as response:
                payload = json.loads(response.read().decode("utf-8") or "null")
        except HTTPError as error:
            detail = error.read(500).decode("utf-8", errors="replace")
            raise ZetarisError(f"HTTP {error.code}: {' '.join(detail.split())}") from error
        except (URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise ZetarisError(f"Cannot reach {self.base_url}: {reason}") from error
        if isinstance(payload, dict):
            if payload.get("error"):
                raise ZetarisError(" ".join(str(payload["error"]).split())[:500])
            return payload.get("data") or []
        return []


def load_ledger(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "migrations" in data and "applied" not in data:
            raise SyncError(
                f"{path} is in the format of the earlier JDBC runner. Move it aside "
                "(for example to ledger.jdbc-old.json) so this tool can start its own."
            )
        return {entry["file"]: entry for entry in data["applied"]}
    except SyncError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SyncError(
            f"{path} is not a valid ledger ({type(error).__name__}). Fix or delete it."
        ) from error


def save_ledger(path: Path, ledger: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"version": LEDGER_VERSION, "applied": [ledger[name] for name in sorted(ledger)]}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def classify(migrations: list[Migration], ledger: dict[str, dict]):
    pending, changed = [], []
    for migration in migrations:
        entry = ledger.get(migration.name)
        if entry is None:
            pending.append(migration)
        elif entry.get("sha256") != migration.sha256:
            changed.append(migration)
    missing = sorted(set(ledger) - {m.name for m in migrations})
    return pending, changed, missing


def check_files(migrations: list[Migration], problems: list[str]) -> bool:
    problems = problems + lint(migrations)
    for problem in problems:
        print(f"error: {problem}")
    return not problems


def apply_one(migration: Migration, env: dict[str, str], client: Client) -> tuple[int, int]:
    secrets = [env[name] for name in migration.placeholders] + [env.get("ZETARIS_API_KEY", "")]
    total = len(migration.statements)
    existing = 0
    for index, template in enumerate(migration.statements, 1):
        try:
            client.run(render(template, env))
        except ZetarisError as error:
            message = redact(str(error), secrets)
            if ALREADY_EXISTS.search(message):
                existing += 1
                print(f"  [{index}/{total}] already exists, skipped")
                continue
            raise SyncError(f"{migration.name} statement {index}/{total} failed: {message}")
        print(f"  [{index}/{total}] ok  {preview(template)}")
    return total, existing


def cmd_status(migrations, problems, ledger_path) -> int:
    ok = check_files(migrations, problems)
    pending, changed, missing = classify(migrations, load_ledger(ledger_path))
    pending_names = {m.name for m in pending}
    changed_names = {m.name for m in changed}
    for migration in migrations:
        if migration.name in changed_names:
            state = "CHANGED after it was applied"
        elif migration.name in pending_names:
            state = "pending"
        else:
            state = "applied"
        print(f"{migration.name}: {state}")
    for name in missing:
        print(f"{name}: in the ledger but the file is gone")
    print(f"{len(pending)} pending, {len(changed)} changed, {len(missing)} missing")
    return 0 if ok and not changed else 1


def cmd_sync(migrations, problems, ledger_path, env, dry_run, client) -> int:
    if not check_files(migrations, problems):
        return 1
    ledger = load_ledger(ledger_path)
    pending, changed, _ = classify(migrations, ledger)
    for migration in changed:
        print(
            f"error: {migration.name} changed after it was applied. "
            "Merged migrations are append-only: put the change in a new numbered file."
        )
    if changed:
        return 1
    names = sorted({name for m in pending for name in m.placeholders})
    if dry_run:
        count = sum(len(m.statements) for m in pending)
        print(f"dry run: {len(pending)} pending file(s), {count} statement(s), nothing sent")
        if names:
            print("placeholders needed: " + ", ".join(names))
        return 0
    if not pending:
        print("nothing to apply")
        return 0
    missing = [name for name in names if not env.get(name)]
    if missing:
        print("error: set these in ingestion/.env (names only): " + ", ".join(missing))
        return 1
    if client is None:
        print("error: no Zetaris connection configured")
        return 1
    for migration in pending:
        print(f"{migration.name}")
        try:
            total, existing = apply_one(migration, env, client)
        except SyncError as error:
            print(f"error: {error}")
            return 1
        ledger[migration.name] = {
            "file": migration.name,
            "sha256": migration.sha256,
            "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "statements": total,
            "skipped_existing": existing,
        }
        save_ledger(ledger_path, ledger)
    print(f"applied {len(pending)} file(s)")
    return 0


def describe_columns(client: Client, view: str) -> list[tuple[str, str]]:
    rows = client.run(f"DESCRIBE {view}")
    return [
        (str(row[0]).lower(), str(row[1]).lower())
        for row in rows
        if row and row[0] and not str(row[0]).startswith("#")
    ]


def check_view(client: Client, spec: ViewSpec) -> str | None:
    """None when the view matches its declared columns and row count, else why not."""
    try:
        actual = describe_columns(client, spec.name)
        count = int(client.run(f"SELECT COUNT(*) FROM {spec.name}")[0][0])
    except ZetarisError as error:
        return f"query failed ({' '.join(str(error).split())[:90]})"
    except (IndexError, ValueError, TypeError):
        return "unexpected answer to DESCRIBE or COUNT"
    expected = list(spec.columns)
    if [name for name, _ in actual] != [name for name, _ in expected]:
        return f"columns are {[n for n, _ in actual]}, expected {[n for n, _ in expected]}"
    for (name, got), (_, want) in zip(actual, expected):
        if got != want:
            return f"column {name} is {got}, expected {want}"
    if spec.min_rows is not None and count < spec.min_rows:
        return f"{count} rows, expected at least {spec.min_rows}"
    return None


def cmd_verify(migrations, problems, ledger_path, secrets, client) -> int:
    ok = check_files(migrations, problems)
    ledger = load_ledger(ledger_path)
    checked = failed = 0
    for migration in migrations:
        for spec in migration.views:
            if migration.name not in ledger:
                print(f"SKIP {spec.name}: {migration.name} is not applied")
                continue
            checked += 1
            reason = check_view(client, spec)
            if reason is None:
                print(f"OK   {spec.name}: {len(spec.columns)} columns, at least {spec.min_rows} rows")
            else:
                failed += 1
                print(f"FAIL {spec.name}: {redact(reason, secrets)}")
    print(f"{checked} view(s) checked, {failed} failed")
    return 0 if ok and not failed else 1


class QuietParser(argparse.ArgumentParser):
    """Usage errors never echo the arguments: one might be a token."""

    def error(self, message: str):
        print("zetaris-sync: invalid arguments (values not printed). Use --help.", file=sys.stderr)
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--migrations", type=Path, default=DEFAULT_MIGRATIONS)
    common.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    common.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser = QuietParser(prog="zetaris_sync.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", parser_class=QuietParser)
    sync = sub.add_parser("sync", parents=[common], help="apply pending migrations")
    sync.add_argument("--dry-run", action="store_true", help="parse and lint; send nothing")
    sub.add_parser("status", parents=[common], help="show applied and pending; send nothing")
    sub.add_parser("verify", parents=[common], help="check declared views; sends read-only queries")
    sub.add_parser("reset", parents=[common], help="not implemented yet")
    return parser


def main(argv: list[str] | None = None, *, client_factory=Client) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    if not args_in or (args_in[0].startswith("-") and args_in[0] not in ("-h", "--help")):
        args_in.insert(0, "sync")
    args = build_parser().parse_args(args_in)

    if args.command == "reset":
        print("zetaris-sync reset: not implemented yet. No SQL was sent.")
        return 2

    try:
        return run_command(args, client_factory)
    except SyncError as error:
        print(f"error: {error}")
        return 1


def run_command(args: argparse.Namespace, client_factory) -> int:
    migrations, problems = discover(args.migrations)
    if args.command == "status":
        return cmd_status(migrations, problems, args.ledger)

    env = load_env_file(args.env_file)
    env.update({k: v for k, v in os.environ.items() if k.startswith(("ZETARIS_", "S3_"))})
    dry_run = getattr(args, "dry_run", False)
    client = None
    if not dry_run:
        if not env.get("ZETARIS_API_KEY"):
            print(
                "error: ZETARIS_API_KEY is not set. Copy ingestion/.env.example to "
                "ingestion/.env and add the key you created in your own Zetaris UI."
            )
            return 1
        client = client_factory(
            env.get("ZETARIS_REST_URL") or DEFAULT_REST_URL,
            env.get("ZETARIS_ORG_ID") or "1",
            env["ZETARIS_API_KEY"],
        )
    if args.command == "verify":
        return cmd_verify(migrations, problems, args.ledger, [env["ZETARIS_API_KEY"]], client)
    return cmd_sync(migrations, problems, args.ledger, env, dry_run, client)


if __name__ == "__main__":
    raise SystemExit(main())
