"""zetaris_sync against a fake local Zetaris. No real Zetaris, no real key."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import threading
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import zetaris_sync as zs  # noqa: E402

API_KEY = "test-key-1234567890"
S3_SECRET = "s3-secret-value-abc"


class FakeZetaris:
    """Records every request. `respond` maps a SQL string to (status, body)."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.respond = lambda sql: (200, {"data": []})
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                headers = {key.lower(): value for key, value in self.headers.items()}
                outer.requests.append({"path": self.path, "headers": headers, "body": body})
                status, payload = outer.respond(body["sql"])
                raw = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/v1.0"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class Workspace:
    """A temporary migrations folder, ledger, and env file."""

    def __init__(self, tmp: Path) -> None:
        self.migrations = tmp / "migrations"
        self.migrations.mkdir()
        self.ledger = tmp / "state" / "ledger.json"
        self.env_file = tmp / "ingestion.env"

    def add(self, name: str, text: str) -> None:
        (self.migrations / name).write_bytes(text.encode("utf-8"))

    def write_env(self, url: str, extra: str = "") -> None:
        self.env_file.write_text(
            f"ZETARIS_REST_URL={url}\nZETARIS_ORG_ID=7\nZETARIS_API_KEY={API_KEY}\n{extra}",
            encoding="utf-8",
        )

    def args(self, *command: str) -> list[str]:
        return [
            *command,
            "--migrations", str(self.migrations),
            "--ledger", str(self.ledger),
            "--env-file", str(self.env_file),
        ]

    def run(self, *command: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = zs.main(self.args(*command))
            except SystemExit as exit_:
                code = int(exit_.code or 0)
        return code, out.getvalue(), err.getvalue()


TWO_STATEMENTS = "CREATE A one\n-- statement\nCREATE B two\n"


class SplitAndHashTest(unittest.TestCase):
    def test_splits_on_marker_line_only(self) -> None:
        text = "-- header\nCREATE A;\n-- statement\nSELECT 1 -- statement in a comment\n-- statement\n-- only a comment\n"
        self.assertEqual(
            zs.split_statements(text),
            ["-- header\nCREATE A", "SELECT 1 -- statement in a comment"],
        )

    def test_crlf_and_lf_files_hash_the_same(self) -> None:
        self.assertEqual(zs.file_sha256(b"A\r\nB\r\n"), zs.file_sha256(b"A\nB\n"))
        self.assertNotEqual(zs.file_sha256(b"A\n"), zs.file_sha256(b"B\n"))


class DiscoverAndLintTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ws = Workspace(Path(self._tmp.name))

    def test_ignores_non_sql_and_flags_bad_names_and_duplicates(self) -> None:
        (self.ws.migrations / "README.md").write_text("notes", encoding="utf-8")
        self.ws.add("001_ok.sql", "SELECT 1")
        self.ws.add("001_dup.sql", "SELECT 2")
        self.ws.add("2_bad.sql", "SELECT 3")
        self.ws.add("003_empty.sql", "-- nothing\n")
        migrations, problems = zs.discover(self.ws.migrations)
        text = "\n".join(problems)
        self.assertIn("2_bad.sql", text)
        self.assertIn("001_ok.sql", text)  # 001_dup sorts first, so 001_ok is the duplicate
        self.assertIn("003_empty.sql", text)
        self.assertEqual([m.name for m in migrations], ["001_dup.sql"])

    def test_lint_flags_literal_secrets_but_not_placeholders(self) -> None:
        self.ws.add("001_bad.sql", 'CREATE X OPTIONS (s3_secret_key "abcdef123456")')
        self.ws.add("002_aws.sql", "CREATE Y -- AKIAABCDEFGHIJKLMNOP")
        self.ws.add("003_good.sql", 'CREATE Z OPTIONS (s3_secret_key "${S3_SECRET_KEY}", token_url "https://x.example/t")')
        migrations, problems = zs.discover(self.ws.migrations)
        self.assertEqual(problems, [])
        flagged = {p.split(":")[0] for p in zs.lint(migrations)}
        self.assertEqual(flagged, {"001_bad.sql", "002_aws.sql"})


class SyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ws = Workspace(Path(self._tmp.name))
        self.fake = FakeZetaris()
        self.addCleanup(self.fake.close)
        self.ws.write_env(self.fake.url)

    def test_applies_in_order_one_statement_per_call_with_documented_headers(self) -> None:
        self.ws.add("002_second.sql", "CREATE C three")
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0, out)
        self.assertEqual([r["body"]["sql"] for r in self.fake.requests], ["CREATE A one", "CREATE B two", "CREATE C three"])
        first = self.fake.requests[0]
        self.assertTrue(first["path"].endswith("/sql-editor/sqls/run"))
        self.assertEqual(first["headers"]["authorization"], f"Bearer {API_KEY}")
        self.assertEqual(first["headers"]["x-org-id"], "7")
        self.assertEqual(first["body"]["source"], "SqlEditor")
        ids = [r["headers"]["x-request-id"] for r in self.fake.requests]
        self.assertEqual(len(set(ids)), 3)
        for value in ids:
            uuid.UUID(value)
        ledger = json.loads(self.ws.ledger.read_text(encoding="utf-8"))
        self.assertEqual([e["file"] for e in ledger["applied"]], ["001_first.sql", "002_second.sql"])
        self.assertEqual(ledger["applied"][0]["sha256"], zs.file_sha256(TWO_STATEMENTS.encode()))

    def test_rerun_sends_nothing(self) -> None:
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        self.assertEqual(self.ws.run("sync")[0], 0)
        sent = len(self.fake.requests)
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.fake.requests), sent)
        self.assertIn("nothing to apply", out)

    def test_changed_applied_file_stops_before_sending(self) -> None:
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        self.assertEqual(self.ws.run("sync")[0], 0)
        sent = len(self.fake.requests)
        self.ws.add("001_first.sql", "CREATE A edited")
        self.ws.add("002_new.sql", "CREATE N new")
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1)
        self.assertIn("changed after it was applied", out)
        self.assertEqual(len(self.fake.requests), sent)

    def test_already_exists_is_skipped_and_recorded(self) -> None:
        self.fake.respond = lambda sql: (400, {"message": "A container named floodsense already exists."}) if sql == "CREATE A one" else (200, {"data": []})
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0, out)
        entry = json.loads(self.ws.ledger.read_text(encoding="utf-8"))["applied"][0]
        self.assertEqual(entry["skipped_existing"], 1)

    def test_sync_exits_nonzero_when_verify_would_fail(self) -> None:
        self.ws.add("001_view.sql", VIEW_MIGRATION)
        self.fake.respond = lambda sql: (
            (200, {"data": [["point_id", "string"], ["date", "string"], ["discharge_m3s", "double"]]})
            if sql.startswith("DESCRIBE")
            else (200, {"data": [["8"]]})
            if sql.startswith("SELECT COUNT")
            else (200, {"data": []})
        )
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL floodsense.discharge_daily", out)
        self.assertIn("column date is string, expected date", out)
        self.assertTrue(self.ws.ledger.is_file())

    def test_already_exists_skip_still_verifies_declared_views(self) -> None:
        def respond(sql: str):
            if "SCHEMASTORE VIEW" in sql:
                return 400, {"message": "A view named discharge_daily already exists."}
            if sql.startswith("DESCRIBE"):
                return 200, {"data": [["point_id", "string"], ["date", "date"], ["discharge_m3s", "double"]]}
            if sql.startswith("SELECT COUNT"):
                return 200, {"data": [["8"]]}
            return 200, {"data": []}

        self.fake.respond = respond
        self.ws.add("001_view.sql", VIEW_MIGRATION)
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0, out)
        self.assertIn("already exists, skipped", out)
        self.assertIn("OK   floodsense.discharge_daily", out)
        entry = json.loads(self.ws.ledger.read_text(encoding="utf-8"))["applied"][0]
        self.assertEqual(entry["skipped_existing"], 1)

    def test_nothing_to_apply_still_verifies_declared_views(self) -> None:
        def respond(sql: str):
            if sql.startswith("DESCRIBE"):
                return 200, {"data": [["point_id", "string"], ["date", "date"], ["discharge_m3s", "double"]]}
            if sql.startswith("SELECT COUNT"):
                return 200, {"data": [["8"]]}
            return 200, {"data": []}

        self.fake.respond = respond
        self.ws.add("001_view.sql", VIEW_MIGRATION)
        self.assertEqual(self.ws.run("sync")[0], 0)
        sent = len(self.fake.requests)
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0, out)
        self.assertIn("nothing to apply", out)
        self.assertIn("OK   floodsense.discharge_daily", out)
        self.assertGreater(len(self.fake.requests), sent)

    def test_036_is_refused_when_a_staged_directory_has_no_csv_header(self) -> None:
        path = "/home/zetaris/customer-data/shared/floodsense_live/pegel_levels"
        sql = (
            "CREATE LIGHTNING FILESTORE TABLE pegel_levels_staged FROM floodsense_live_src\n"
            "FORMAT csv\n"
            f'OPTIONS (path "file://{path}", header "true");\n'
        )
        self.ws.add("036_reregister_live_filestore.sql", sql)
        with patch.object(zs, "read_staged_csv_headers", return_value={path: ""}):
            code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1, out)
        self.assertIn("refuse 036", out)
        self.assertIn(path, out)
        self.assertEqual(self.fake.requests, [])

    def test_036_applies_when_each_staged_directory_has_a_csv_header(self) -> None:
        path = "/home/zetaris/customer-data/shared/floodsense_live/pegel_levels"
        sql = (
            "CREATE LIGHTNING FILESTORE TABLE pegel_levels_staged FROM floodsense_live_src\n"
            "FORMAT csv\n"
            f'OPTIONS (path "file://{path}", header "true");\n'
        )
        self.ws.add("036_reregister_live_filestore.sql", sql)
        with patch.object(
            zs, "read_staged_csv_headers", return_value={path: "station,water,time"}
        ):
            code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.fake.requests), 1)

    def test_dry_run_does_not_ask_docker_about_036_headers(self) -> None:
        path = "/home/zetaris/customer-data/shared/floodsense_live/pegel_levels"
        sql = (
            "CREATE LIGHTNING FILESTORE TABLE pegel_levels_staged FROM floodsense_live_src\n"
            f'OPTIONS (path "file://{path}", header "true");\n'
        )
        self.ws.add("036_reregister_live_filestore.sql", sql)

        def _boom(*_args, **_kwargs):
            raise AssertionError("dry run must not inspect staged headers")

        with patch.object(zs, "read_staged_csv_headers", _boom):
            code, out, _ = self.ws.run("sync", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("nothing sent", out)
        self.assertEqual(self.fake.requests, [])

    def test_read_staged_csv_headers_from_docker(self) -> None:
        path = "/home/zetaris/customer-data/shared/floodsense_live/pegel_levels"
        calls: list[list[str]] = []

        def fake_run(argv, **_kwargs):
            calls.append(list(argv))

            class _Done:
                returncode = fake_run.code
                stdout = fake_run.stdout
                stderr = fake_run.stderr

            return _Done()

        fake_run.code = 0
        fake_run.stdout = f"{path}\t\n"
        fake_run.stderr = ""
        with patch("zetaris_sync.subprocess.run", fake_run):
            missing = zs.read_staged_csv_headers([path], "zetaris-driver-1")
        self.assertEqual(missing, {path: ""})
        self.assertEqual(
            zs.csv_header_problems(missing),
            [f"{path}: no CSV header"],
        )
        self.assertEqual(calls[0][:3], ["docker", "exec", "zetaris-driver-1"])
        self.assertIn(path, calls[0][-1])

        fake_run.stdout = f"{path}\tstation,water,time\n"
        with patch("zetaris_sync.subprocess.run", fake_run):
            header_only = zs.read_staged_csv_headers([path], "zetaris-driver-1")
        self.assertEqual(header_only, {path: "station,water,time"})
        self.assertEqual(zs.csv_header_problems(header_only), [])

        fake_run.code = 1
        fake_run.stdout = ""
        fake_run.stderr = "No such container"
        with patch("zetaris_sync.subprocess.run", fake_run):
            with self.assertRaises(zs.SyncError) as raised:
                zs.read_staged_csv_headers([path], "missing-driver")
        self.assertIn("missing-driver", str(raised.exception))
        self.assertIn("docker exit 1", str(raised.exception))

    def test_a_blank_header_line_is_refused_and_a_name_line_is_kept(self) -> None:
        self.assertEqual(
            zs.csv_header_problems({"/data/pegel_levels": ""}),
            ["/data/pegel_levels: no CSV header"],
        )
        self.assertEqual(
            zs.csv_header_problems({"/data/pegel_levels": None}),
            ["/data/pegel_levels: no CSV header"],
        )
        self.assertEqual(
            zs.csv_header_problems({"/data/pegel_levels": "station,water,time"}),
            [],
        )

    def test_dry_run_does_not_verify(self) -> None:
        self.ws.env_file.unlink()
        self.ws.add("001_view.sql", VIEW_MIGRATION)
        code, out, _ = self.ws.run("sync", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertNotIn("OK   ", out)
        self.assertNotIn("FAIL ", out)
        self.assertEqual(self.fake.requests, [])

    def test_other_error_stops_and_leaves_the_file_unrecorded(self) -> None:
        self.fake.respond = lambda sql: (500, {"message": "boom"}) if "two" in sql else (200, {"data": []})
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        self.ws.add("002_next.sql", "CREATE C three")
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1)
        self.assertIn("statement 2/2 failed", out)
        self.assertFalse(self.ws.ledger.exists())
        self.assertEqual(len(self.fake.requests), 2)

    def test_placeholders_are_filled_but_secrets_never_printed(self) -> None:
        self.ws.write_env(self.fake.url, f"S3_SECRET_KEY={S3_SECRET}\n")
        self.ws.add("001_s3.sql", 'CREATE T OPTIONS (s3_secret_key "${S3_SECRET_KEY}")')
        self.fake.respond = lambda sql: (400, {"message": f"bad option near {S3_SECRET} and {API_KEY}"})
        code, out, err = self.ws.run("sync")
        self.assertEqual(code, 1)
        self.assertIn(S3_SECRET, self.fake.requests[0]["body"]["sql"])
        for secret in (S3_SECRET, API_KEY):
            self.assertNotIn(secret, out + err)
        self.assertIn("***", out)

    def test_missing_placeholder_value_stops_before_any_call(self) -> None:
        self.ws.add("001_s3.sql", 'CREATE T OPTIONS (s3_secret_key "${S3_SECRET_KEY}")')
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1)
        self.assertIn("S3_SECRET_KEY", out)
        self.assertEqual(self.fake.requests, [])

    def test_missing_api_key_explains_how_to_fix(self) -> None:
        self.ws.env_file.write_text("ZETARIS_ORG_ID=1\n", encoding="utf-8")
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1)
        self.assertIn("ingestion/.env", out)
        self.assertEqual(self.fake.requests, [])

    def test_dry_run_needs_no_env_and_sends_nothing(self) -> None:
        self.ws.env_file.unlink()
        self.ws.add("001_first.sql", 'CREATE T OPTIONS (k "${S3_ENDPOINT}")\n-- statement\nSELECT 1')
        code, out, _ = self.ws.run("sync", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("S3_ENDPOINT", out)
        self.assertEqual(self.fake.requests, [])
        self.assertFalse(self.ws.ledger.exists())

    def test_dry_run_fails_on_lint_problems(self) -> None:
        self.ws.add("001_bad.sql", 'CREATE X OPTIONS (password "hunter2hunter2")')
        code, out, _ = self.ws.run("sync", "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("literal secret", out)

    def test_old_jdbc_runner_ledger_is_refused_not_overwritten(self) -> None:
        self.ws.ledger.parent.mkdir(parents=True)
        old = '{"format_version": 1, "migrations": {"001_x.sql": "abc"}}'
        self.ws.ledger.write_text(old, encoding="utf-8")
        self.ws.add("001_first.sql", TWO_STATEMENTS)
        for command in ("status", "sync"):
            code, out, _ = self.ws.run(command)
            self.assertEqual(code, 1)
            self.assertIn("earlier JDBC runner", out)
        self.assertEqual(self.ws.ledger.read_text(encoding="utf-8"), old)
        self.assertEqual(self.fake.requests, [])

    def test_status_reports_applied_pending_and_changed(self) -> None:
        self.ws.add("001_first.sql", "CREATE A one")
        self.ws.run("sync")
        self.ws.add("002_next.sql", "CREATE B two")
        code, out, _ = self.ws.run("status")
        self.assertEqual(code, 0)
        self.assertIn("001_first.sql: applied", out)
        self.assertIn("002_next.sql: pending", out)
        self.ws.add("001_first.sql", "CREATE A edited")
        code, out, _ = self.ws.run("status")
        self.assertEqual(code, 1)
        self.assertIn("CHANGED", out)

    def test_status_fails_when_a_ledger_file_is_gone(self) -> None:
        self.ws.ledger.parent.mkdir(parents=True)
        self.ws.ledger.write_text(
            json.dumps({"version": 1, "applied": [{"file": "001_gone.sql", "sha256": "abc"}]}),
            encoding="utf-8",
        )
        self.ws.add("002_ok.sql", "SELECT 1")
        code, out, _ = self.ws.run("status")
        self.assertEqual(code, 1)
        self.assertIn("001_gone.sql: in the ledger but the file is gone", out)

    def test_sync_fails_when_a_ledger_file_is_gone_and_sends_nothing(self) -> None:
        self.ws.ledger.parent.mkdir(parents=True)
        self.ws.ledger.write_text(
            json.dumps({"version": 1, "applied": [{"file": "001_gone.sql", "sha256": "abc"}]}),
            encoding="utf-8",
        )
        self.ws.add("002_ok.sql", "SELECT 1")
        for command in (("sync",), ("sync", "--dry-run")):
            code, out, _ = self.ws.run(*command)
            self.assertEqual(code, 1, out)
            self.assertIn("001_gone.sql: in the ledger but the file is gone", out)
            self.assertEqual(self.fake.requests, [])

    def test_sync_verifies_applied_views_when_a_later_migration_fails(self) -> None:
        def respond(sql: str):
            if "CREATE C" in sql:
                return 500, {"message": "boom"}
            if sql.startswith("DESCRIBE"):
                return 200, {"data": [["point_id", "string"], ["date", "date"], ["discharge_m3s", "double"]]}
            if sql.startswith("SELECT COUNT"):
                return 200, {"data": [["8"]]}
            return 200, {"data": []}

        self.fake.respond = respond
        self.ws.add("001_view.sql", VIEW_MIGRATION)
        self.ws.add("002_bad.sql", "CREATE C three")
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 1, out)
        self.assertIn("statement 1/1 failed", out)
        self.assertIn("verifying views already applied", out)
        self.assertIn("OK   floodsense.discharge_daily", out)
        applied = [entry["file"] for entry in json.loads(self.ws.ledger.read_text(encoding="utf-8"))["applied"]]
        self.assertEqual(applied, ["001_view.sql"])


VIEW_MIGRATION = """-- view: floodsense.discharge_daily
-- columns: point_id string, date date, discharge_m3s double
-- min_rows: 8
CREATE OR REPLACE SCHEMASTORE VIEW discharge_daily WITH CONTAINER floodsense AS SELECT 1
"""


class ViewSpecTest(unittest.TestCase):
    def test_parses_header_comments(self) -> None:
        text = VIEW_MIGRATION + "-- view: floodsense_seed.x\n-- columns: a string\n-- min_rows: 1\n"
        specs = zs.parse_view_specs(text)
        self.assertEqual([s.name for s in specs], ["floodsense.discharge_daily", "floodsense_seed.x"])
        self.assertEqual(specs[0].columns, (("point_id", "string"), ("date", "date"), ("discharge_m3s", "double")))
        self.assertEqual(specs[0].min_rows, 8)

    def test_lint_wants_columns_and_min_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Workspace(Path(tmp))
            ws.add("001_v.sql", "-- view: floodsense.v\nCREATE OR REPLACE SCHEMASTORE VIEW v WITH CONTAINER floodsense AS SELECT 1")
            ws.add("002_w.sql", "-- view: Bad.Name\n-- columns: a string\n-- min_rows: 1\nSELECT 1")
            migrations, problems = zs.discover(ws.migrations)
            self.assertEqual(problems, [])
            text = "\n".join(zs.lint(migrations))
            self.assertIn("001_v.sql: view floodsense.v needs", text)
            self.assertIn("002_w.sql: view name", text)


class VerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ws = Workspace(Path(self._tmp.name))
        self.fake = FakeZetaris()
        self.addCleanup(self.fake.close)
        self.ws.write_env(self.fake.url)
        self.ws.add("001_view.sql", VIEW_MIGRATION)
        self.columns = [["point_id", "string", None], ["date", "date", None], ["discharge_m3s", "double", None]]
        self.rows = 136

        def respond(sql: str):
            if sql.startswith("DESCRIBE"):
                return 200, {"data": self.columns}
            if sql.startswith("SELECT COUNT"):
                return 200, {"data": [[str(self.rows)]]}
            return 200, {"data": []}

        self.fake.respond = respond

    def sync_then_verify(self) -> tuple[int, str]:
        self.assertEqual(self.ws.run("sync")[0], 0)
        code, out, _ = self.ws.run("verify")
        return code, out

    def test_ok_when_columns_types_and_rows_match(self) -> None:
        code, out = self.sync_then_verify()
        self.assertEqual(code, 0, out)
        self.assertIn("OK   floodsense.discharge_daily: 3 columns, at least 8 rows", out)

    def test_fails_on_wrong_type_name_and_row_count(self) -> None:
        self.assertEqual(self.ws.run("sync")[0], 0)
        self.columns[1][1] = "string"
        code, out, _ = self.ws.run("verify")
        self.assertEqual(code, 1)
        self.assertIn("column date is string, expected date", out)
        self.columns[1][1] = "date"
        self.columns[0][0] = "id"
        self.assertIn("columns are", self.ws.run("verify")[1])
        self.columns[0][0] = "point_id"
        self.rows = 3
        self.assertIn("3 rows, expected at least 8", self.ws.run("verify")[1])

    def test_fails_when_the_view_is_missing(self) -> None:
        self.assertEqual(self.ws.run("sync")[0], 0)
        self.fake.respond = lambda sql: (400, {"msg": "TABLE_OR_VIEW_NOT_FOUND"})
        code, out, _ = self.ws.run("verify")
        self.assertEqual(code, 1)
        self.assertIn("FAIL floodsense.discharge_daily: query failed", out)

    def test_skips_views_whose_migration_is_not_applied(self) -> None:
        code, out, _ = self.ws.run("verify")
        self.assertEqual(code, 1)
        self.assertIn("SKIP floodsense.discharge_daily", out)
        self.assertIn("none are applied", out)
        self.assertEqual(self.fake.requests, [])

    def test_verify_uses_the_latest_applied_declaration(self) -> None:
        (self.ws.migrations / "001_view.sql").unlink()
        self.ws.add(
            "002_old.sql",
            "-- view: floodsense.v\n-- columns: a string\n-- min_rows: 1\nSELECT 1\n",
        )
        self.ws.add(
            "003_new.sql",
            "-- view: floodsense.v\n-- columns: a string, synthetic string\n-- min_rows: 1\nSELECT 2\n",
        )
        self.columns[:] = [["a", "string", None], ["synthetic", "string", None]]
        self.rows = 1
        code, out, _ = self.ws.run("sync")
        self.assertEqual(code, 0, out)
        self.assertIn("OK   floodsense.v: 2 columns, at least 1 rows", out)
        self.assertEqual(out.count("OK   floodsense.v"), 1)

    def test_output_is_identical_on_a_second_run(self) -> None:
        self.assertEqual(self.ws.run("sync")[0], 0)
        self.assertEqual(self.ws.run("verify")[1], self.ws.run("verify")[1])


class CommandLineTest(unittest.TestCase):
    def test_usage_errors_never_echo_arguments(self) -> None:
        secret = "super-secret-token-value"
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as raised:
                zs.main([secret, "--token", secret])
        self.assertEqual(raised.exception.code, 2)
        self.assertNotIn(secret, out.getvalue() + err.getvalue())

    def test_reset_says_it_is_not_implemented(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = zs.main(["reset"])
        self.assertEqual(code, 2)
        self.assertIn("not implemented", out.getvalue())


if __name__ == "__main__":
    unittest.main()
