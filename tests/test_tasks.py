"""Non-Docker behaviour of tasks.py. These tests do not need Docker or Make."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tasks  # noqa: E402


class TaskTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in tasks.ENV_EXAMPLES:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"example {rel}\n".encode())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_init_env_copies_missing_and_does_not_overwrite(self) -> None:
        existing = self.root / "api" / ".env"
        existing.write_bytes(b"keep-me\n")
        out = io.StringIO()
        with redirect_stdout(out):
            code = tasks.init_env(self.root)
            again = tasks.init_env(self.root)
        self.assertEqual(code, 0)
        self.assertEqual(again, 0)
        self.assertEqual(existing.read_bytes(), b"keep-me\n")
        for rel in tasks.ENV_EXAMPLES:
            dest = (self.root / rel).with_name(".env")
            self.assertTrue(dest.is_file(), rel)
        root_env = (self.root / ".env").read_bytes()
        self.assertEqual(root_env, b"example .env.example\n")
        self.assertIn("copied 5, kept 1", out.getvalue())
        self.assertIn("copied 0, kept 6", out.getvalue())

    def test_init_env_stops_when_an_example_is_missing(self) -> None:
        (self.root / "ui" / ".env.example").unlink()
        err = io.StringIO()
        with redirect_stderr(err):
            code = tasks.init_env(self.root)
        self.assertEqual(code, 1)
        self.assertIn("ui/.env.example", err.getvalue())
        self.assertFalse((self.root / ".env").exists())
        self.assertFalse((self.root / "api" / ".env").exists())

    def test_check_env_names_every_missing_file(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = tasks.check_env(self.root)
        text = err.getvalue()
        self.assertEqual(code, 1)
        for rel in tasks.REQUIRED_ENV:
            self.assertIn(rel, text)
        self.assertIn("init-env", text)
        self.assertNotIn(tasks.PGVECTOR_ENV, text)

    def test_check_env_passes_without_pgvector(self) -> None:
        for rel in tasks.REQUIRED_ENV:
            (self.root / rel).write_bytes(b"x\n")
        out = io.StringIO()
        with redirect_stdout(out):
            code = tasks.check_env(self.root)
        self.assertEqual(code, 0)
        self.assertIn("env files present", out.getvalue())

    def test_up_all_requires_pgvector_env(self) -> None:
        for rel in tasks.REQUIRED_ENV:
            (self.root / rel).write_bytes(b"x\n")

        def runner(argv: list[str], cwd: Path) -> int:
            raise AssertionError(argv)

        err = io.StringIO()
        with redirect_stderr(err):
            code = tasks.cmd_up_all(self.root, runner)
        self.assertEqual(code, 1)
        self.assertIn(tasks.PGVECTOR_ENV, err.getvalue())

    def test_up_does_not_call_docker_when_env_is_missing(self) -> None:
        def runner(argv: list[str], cwd: Path) -> int:
            raise AssertionError(argv)

        with redirect_stderr(io.StringIO()):
            code = tasks.cmd_up(self.root, runner)
        self.assertEqual(code, 1)

    def test_down_pins_project_and_keeps_volumes_without_env_files(self) -> None:
        calls: list[tuple[list[str], Path]] = []

        def runner(argv: list[str], cwd: Path) -> int:
            calls.append((argv, cwd))
            return 0

        self.assertEqual(tasks.cmd_down(self.root, runner), 0)
        self.assertEqual(len(calls), 1)
        argv, cwd = calls[0]
        self.assertEqual(cwd, self.root)
        self.assertEqual(argv[:4], ["docker", "compose", "-p", "floodsense-app"])
        self.assertEqual(argv[4], "--project-directory")
        self.assertEqual(argv[5], str(self.root))
        self.assertEqual(argv[6], "-f")
        self.assertEqual(argv[7], str(self.root / "compose.yaml"))
        self.assertEqual(
            argv[8:],
            ["--profile", "rag", "--profile", "cache", "down"],
        )
        self.assertNotIn("-v", argv)
        self.assertNotIn("--volumes", argv)

    def test_up_argv_has_no_profiles(self) -> None:
        for rel in tasks.REQUIRED_ENV:
            (self.root / rel).write_bytes(b"x\n")
        seen: list[list[str]] = []

        def runner(argv: list[str], cwd: Path) -> int:
            seen.append(argv)
            return 0

        with redirect_stdout(io.StringIO()):
            self.assertEqual(tasks.cmd_up(self.root, runner), 0)
        self.assertEqual(seen[0][-3:], ["up", "-d", "--build"])
        self.assertNotIn("--profile", seen[0])
        self.assertIn("-p", seen[0])
        self.assertIn("floodsense-app", seen[0])

    def test_zetaris_sync_uses_this_interpreter(self) -> None:
        seen: list[list[str]] = []

        def runner(argv: list[str], cwd: Path) -> int:
            seen.append(argv)
            return 0

        self.assertEqual(tasks.cmd_zetaris_sync(self.root, runner), 0)
        self.assertEqual(seen[0][0], sys.executable)
        self.assertEqual(seen[0][1], str(self.root / "scripts" / "zetaris_sync.py"))

    def test_test_steps_use_this_interpreter_and_include_task_tests(self) -> None:
        steps = tasks.test_steps(self.root)
        self.assertTrue(all(argv[0] == sys.executable for _, argv in steps))
        self.assertIn(self.root / "api", [cwd for cwd, _ in steps])
        self.assertIn(self.root / "agents", [cwd for cwd, _ in steps])
        discovered = [(cwd, argv) for cwd, argv in steps if "discover" in argv]
        starts = [(cwd, argv[argv.index("-s") + 1]) for cwd, argv in discovered]
        self.assertIn((self.root / "api", "tests"), starts)
        self.assertIn((self.root, "scripts/tests"), starts)
        self.assertIn((self.root, "tests"), starts)
        self.assertIn((self.root, "contracts/tests"), starts)
        compile_argv = steps[0][1]
        self.assertIn("contracts/python", compile_argv)
        self.assertIn("contracts/tests", compile_argv)

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
        )

    def _install_fake_tsc(self) -> None:
        tsc = self.root / "ui" / "node_modules" / "typescript" / "bin" / "tsc"
        tsc.parent.mkdir(parents=True, exist_ok=True)
        tsc.write_text("", encoding="utf-8")

    def test_forbidden_env_paths(self) -> None:
        self.assertTrue(tasks.is_forbidden_env_path("api/.env"))
        self.assertTrue(tasks.is_forbidden_env_path(".env.local"))
        self.assertTrue(tasks.is_forbidden_env_path("API/.ENV"))
        self.assertTrue(tasks.is_forbidden_env_path(".env.example.bak"))
        self.assertFalse(tasks.is_forbidden_env_path(".env.example"))
        self.assertFalse(tasks.is_forbidden_env_path("api/.env.example"))
        self.assertFalse(tasks.is_forbidden_env_path("Foo.env.example"))
        self.assertFalse(tasks.is_forbidden_env_path("notes/readme.md"))
        self.assertFalse(tasks.is_forbidden_env_path(".environment"))

    def test_check_tracked_env_rejects_a_staged_env_file(self) -> None:
        self._git("init")
        env = self.root / "api" / ".env"
        env.write_text("TOKEN=example\n", encoding="utf-8")
        self._git("add", "-A")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = tasks.check_tracked_env(self.root)
        self.assertEqual(code, 1)
        listed = [
            line.strip()
            for line in err.getvalue().splitlines()
            if line.startswith("  ")
        ]
        self.assertEqual(listed, ["api/.env"])

    def test_this_repository_tracks_no_env_file(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = tasks.check_tracked_env(tasks.ROOT)
        self.assertEqual(code, 0)
        self.assertIn("no tracked .env files", out.getvalue())

    def test_lint_runs_ruff_and_typecheck_without_gitleaks(self) -> None:
        self._git("init")
        self._git("add", "-A")
        self._install_fake_tsc()
        calls: list[list[str]] = []

        def runner(argv: list[str], cwd: Path) -> int:
            calls.append(argv)
            return 0

        out = io.StringIO()
        with redirect_stdout(out):
            code = tasks.cmd_lint(
                self.root,
                runner,
                node="node",
                gitleaks=None,
                resolve_tools=False,
                require_gitleaks=False,
            )
        self.assertEqual(code, 0)
        self.assertIn("gitleaks not on PATH", out.getvalue())
        flat = [" ".join(argv) for argv in calls]
        self.assertTrue(any("-m ruff check" in text for text in flat))
        self.assertTrue(any("ui/tsconfig.json" in text.replace("\\", "/") for text in flat))
        self.assertTrue(
            any("contracts/tsconfig.json" in text.replace("\\", "/") for text in flat)
        )
        self.assertFalse(any(text.startswith("gitleaks") for text in flat))

    def test_lint_includes_gitleaks_when_it_is_on_path(self) -> None:
        self._git("init")
        self._install_fake_tsc()
        calls: list[list[str]] = []

        def runner(argv: list[str], cwd: Path) -> int:
            calls.append(argv)
            return 0

        with redirect_stdout(io.StringIO()):
            code = tasks.cmd_lint(
                self.root,
                runner,
                node="node",
                gitleaks="gitleaks",
                resolve_tools=False,
                require_gitleaks=False,
            )
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][0], "gitleaks")
        self.assertIn("detect", calls[0])
        self.assertIn("--redact", calls[0])

    def test_lint_fails_when_gitleaks_is_required_and_missing(self) -> None:
        self._git("init")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = tasks.cmd_lint(
                self.root,
                self._fail_runner,
                node="node",
                gitleaks=None,
                resolve_tools=False,
                require_gitleaks=True,
            )
        self.assertEqual(code, 1)
        self.assertIn("FLOODSENSE_REQUIRE_GITLEAKS", err.getvalue())

    def test_lint_names_npm_ci_when_typescript_is_missing(self) -> None:
        self._git("init")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = tasks.cmd_lint(
                self.root,
                self._fail_runner,
                node="node",
                gitleaks=None,
                resolve_tools=False,
                require_gitleaks=False,
            )
        self.assertEqual(code, 1)
        self.assertIn("npm ci", err.getvalue())

    def test_unknown_command_exits_nonzero(self) -> None:
        with self.assertRaises(SystemExit) as caught, redirect_stderr(io.StringIO()):
            tasks.main(["nope"], root=self.root)
        self.assertNotEqual(caught.exception.code, 0)

    def test_missing_executable_returns_127(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = tasks.execute(
                ["floodsense-missing-bin-9f3a", "--version"],
                self.root,
            )
        self.assertEqual(code, 127)
        self.assertIn("Command not found", err.getvalue())

    def test_runner_source_does_not_invoke_a_shell(self) -> None:
        source = Path(tasks.__file__).read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("python3", source)

    @staticmethod
    def _fail_runner(argv: list[str], cwd: Path) -> int:
        raise AssertionError(argv)


if __name__ == "__main__":
    unittest.main()
