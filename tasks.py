"""Cross-platform tasks for FloodSense EU.

Windows PowerShell 5.x, PowerShell 7, cmd, macOS, and Linux. Stdlib only.
No Make and no shell, so PowerShell 5 (which has no &&) can run every command.

    python tasks.py <command>
    py tasks.py <command>

`engines-test` runs `npm test` and `npm run conformance` in engines/.
That needs Node.js 22.18 or newer. The lint and UI CI job stays on Node 20,
which cannot run the sidecar. The engines CI job is the one that runs this.

Docker commands always pass -p floodsense-app, plus an explicit compose file
and project directory. An exported COMPOSE_PROJECT_NAME or COMPOSE_FILE
cannot attach this stack to another project, such as a local Zetaris stack.
`down` does not delete volumes and does not need pgvector/.env.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = "floodsense-app"

# Posix relative paths. Path() accepts these on Windows.
ENV_EXAMPLES: tuple[str, ...] = (
    ".env.example",
    "api/.env.example",
    "agents/.env.example",
    "ui/.env.example",
    "ingestion/.env.example",
    "pgvector/.env.example",
    "engines/.env.example",
)
REQUIRED_ENV: tuple[str, ...] = ("api/.env", "agents/.env", "ui/.env")
PGVECTOR_ENV = "pgvector/.env"
# engines/ runs TypeScript with Node's built-in loader. Node 20 cannot.
ENGINES_MIN_NODE: tuple[int, ...] = (22, 18)

# argv, cwd. Callers pass a list so nothing is parsed by a shell.
Runner = Callable[[list[str], Path], int]


def compose_argv(root: Path, *args: str) -> list[str]:
    """Pin project, file, and directory. Flags stay in front of the subcommand."""
    return [
        "docker",
        "compose",
        "-p",
        PROJECT,
        "--project-directory",
        str(root),
        "-f",
        str(root / "compose.yaml"),
        *args,
    ]


def up_argv(root: Path) -> list[str]:
    return compose_argv(root, "up", "-d", "--build")


def up_all_argv(root: Path) -> list[str]:
    return compose_argv(
        root,
        "--profile",
        "rag",
        "--profile",
        "cache",
        "up",
        "-d",
        "--build",
    )


def down_argv(root: Path) -> list[str]:
    # Profiles so optional containers stop too. No -v / --volumes.
    return compose_argv(root, "--profile", "rag", "--profile", "cache", "down")


def config_argv(root: Path) -> list[str]:
    return compose_argv(root, "--profile", "rag", "--profile", "cache", "config")


def missing_env(root: Path, *, require_pgvector: bool = False) -> list[str]:
    needed = list(REQUIRED_ENV)
    if require_pgvector:
        needed.append(PGVECTOR_ENV)
    return [rel for rel in needed if not (root / rel).is_file()]


def check_env(root: Path, *, require_pgvector: bool = False, quiet_ok: bool = False) -> int:
    missing = missing_env(root, require_pgvector=require_pgvector)
    if not missing:
        if not quiet_ok:
            print("env files present")
        return 0
    launcher = Path(sys.executable).name
    print("Missing env files. They are git-ignored. Create them with:", file=sys.stderr)
    print(f"  {launcher} tasks.py init-env", file=sys.stderr)
    for rel in missing:
        example = Path(rel).with_name(".env.example").as_posix()
        print(f"  missing {rel} (example {example})", file=sys.stderr)
    return 1


def init_env(root: Path) -> int:
    """Copy each missing example to .env. Never overwrites an existing file."""
    planned: list[tuple[str, Path, Path]] = []
    for rel in ENV_EXAMPLES:
        src = root / rel
        if not src.is_file():
            print(f"Missing example {rel}", file=sys.stderr)
            return 1
        planned.append((rel, src, src.with_name(".env")))

    copied = 0
    kept = 0
    for rel, src, dest in planned:
        dest_rel = dest.relative_to(root).as_posix()
        if dest.exists():
            print(f"keep   {dest_rel}")
            kept += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        print(f"copy   {rel} -> {dest_rel}")
        copied += 1
    print(
        f"init-env: copied {copied}, kept {kept}. "
        "Fill secrets in the copies. Do not commit .env files."
    )
    return 0


def execute(argv: list[str], cwd: Path) -> int:
    print("+ " + shlex.join(argv), flush=True)
    try:
        completed = subprocess.run(argv, cwd=cwd, check=False)
    except FileNotFoundError:
        print(
            f"Command not found: {argv[0]}. Install it and put it on PATH.",
            file=sys.stderr,
        )
        return 127
    return int(completed.returncode)


def cmd_up(root: Path, runner: Runner) -> int:
    code = check_env(root, quiet_ok=True)
    if code != 0:
        return code
    return runner(up_argv(root), root)


def cmd_up_all(root: Path, runner: Runner) -> int:
    code = check_env(root, require_pgvector=True, quiet_ok=True)
    if code != 0:
        return code
    return runner(up_all_argv(root), root)


def cmd_down(root: Path, runner: Runner) -> int:
    # No env check. A missing pgvector/.env must not trap a running stack.
    return runner(down_argv(root), root)


def cmd_config(root: Path, runner: Runner) -> int:
    print(
        "config prints resolved environment. Do not log it when .env files hold real tokens.",
        file=sys.stderr,
    )
    return runner(config_argv(root), root)


def cmd_pegel_poll(root: Path, runner: Runner, extra: list[str]) -> int:
    script = root / "ingestion" / "feeds" / "pegel_poll.py"
    return runner([sys.executable, str(script), *extra], root)


def cmd_zetaris_sync(root: Path, runner: Runner) -> int:
    script = root / "scripts" / "zetaris_sync.py"
    return runner([sys.executable, str(script)], root)


# tests/test_tasks.py requires every test step to start with this interpreter.
# The script still runs `npm test` in ui/ (Vitest).
_UI_NPM_TEST = """\
import shutil
import subprocess
import sys
from pathlib import Path

npm = shutil.which("npm")
if npm is None:
    print(
        "npm is not on PATH. Install Node.js 20, then run npm ci in ui/.",
        file=sys.stderr,
    )
    raise SystemExit(1)
if not (Path.cwd() / "node_modules" / "vitest" / "package.json").is_file():
    print("Vitest is not installed. From the ui directory, run:", file=sys.stderr)
    print("  npm ci", file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(subprocess.call([npm, "test"]))
"""


def test_steps(root: Path) -> list[tuple[Path, list[str]]]:
    exe = sys.executable
    return [
        (
            root,
            [
                exe,
                "-m",
                "compileall",
                "-q",
                "api/app",
                "agents/floodsense_agents",
                "scripts",
                "tests",
                "tasks.py",
                "contracts/python",
                "contracts/tests",
            ],
        ),
        (root / "api", [exe, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        (root / "agents", [exe, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        (root, [exe, "-m", "unittest", "discover", "-s", "scripts/tests", "-v"]),
        (root, [exe, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        (root, [exe, "-m", "unittest", "discover", "-s", "contracts/tests", "-v"]),
        (root / "ui", [exe, "-c", _UI_NPM_TEST]),
    ]


def cmd_test(root: Path, runner: Runner) -> int:
    for cwd, argv in test_steps(root):
        code = runner(argv, cwd)
        if code != 0:
            return code
    return 0


def parse_node_version(text: str) -> tuple[int, ...] | None:
    """Parse `v22.18.0` (or with a trailing label) into a version tuple."""
    raw = text.strip().lstrip("vV")
    parts: list[int] = []
    for piece in raw.split("."):
        digits: list[str] = []
        for char in piece:
            if char.isdigit():
                digits.append(char)
            else:
                break
        if not digits:
            break
        parts.append(int("".join(digits)))
    return tuple(parts) if parts else None


def node_version_text(node: str) -> str | None:
    try:
        completed = subprocess.run(
            [node, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def engines_test_steps(root: Path, npm: str) -> list[tuple[Path, list[str]]]:
    engines = root / "engines"
    return [
        (engines, [npm, "test"]),
        (engines, [npm, "run", "conformance"]),
    ]


def cmd_engines_test(root: Path, runner: Runner, *, node: str | None = None) -> int:
    """npm test and npm run conformance. Requires Node.js 22.18 or newer.

    The lint job and the UI image stay on Node 20. That interpreter cannot
    run engines/. CI calls this from the engines job, which installs 22.18.
    """
    if node is None:
        node = shutil.which("node")
    if not node:
        print(
            "node is not on PATH. engines tests need Node.js 22.18 or newer.",
            file=sys.stderr,
        )
        print(
            "The lint and UI CI job stays on Node 20 and does not run this step.",
            file=sys.stderr,
        )
        return 1
    reported = node_version_text(node)
    version = parse_node_version(reported or "")
    if version is None or version < ENGINES_MIN_NODE:
        found = reported or "unknown"
        print(
            f"engines tests need Node.js 22.18 or newer (this interpreter is {found}).",
            file=sys.stderr,
        )
        print(
            "The lint and UI CI job stays on Node 20, which cannot run engines/. "
            "Install Node.js 22.18 or newer and run: python tasks.py engines-test",
            file=sys.stderr,
        )
        return 1
    npm = shutil.which("npm")
    if not npm:
        print("npm is not on PATH. engines tests need npm with Node.js 22.18.", file=sys.stderr)
        return 1
    for cwd, argv in engines_test_steps(root, npm):
        code = runner(argv, cwd)
        if code != 0:
            return code
    return 0


def is_forbidden_env_path(path: str) -> bool:
    """True for a tracked .env file. `.env.example` and `*.env.example` are allowed."""
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name == ".env.example" or name.endswith(".env.example"):
        return False
    return name == ".env" or name.startswith(".env.")


def tracked_paths(root: Path) -> list[str] | None:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        sys.stderr.buffer.write(completed.stderr)
        print("git ls-files failed.", file=sys.stderr)
        return None
    raw = completed.stdout.decode("utf-8", errors="surrogateescape")
    return [part for part in raw.split("\0") if part]


def check_tracked_env(root: Path) -> int:
    """Fail if git tracks a filled env file. Examples named `.env.example` stay allowed."""
    paths = tracked_paths(root)
    if paths is None:
        return 1
    bad = [path for path in paths if is_forbidden_env_path(path)]
    if not bad:
        print("no tracked .env files")
        return 0
    print(
        "Tracked env files are not allowed. Commit .env.example only.",
        file=sys.stderr,
    )
    for rel in bad:
        print(f"  {rel}", file=sys.stderr)
    return 1


def typescript_bin(root: Path) -> Path:
    return root / "ui" / "node_modules" / "typescript" / "bin" / "tsc"


def resolve_gitleaks_log_opts(explicit: str | None = None) -> str:
    """Arguments for `gitleaks detect --log-opts`.

    An empty `--log-opts` makes gitleaks 8.30 run `git log --all`, which
    scans every fetched branch. CI sets FLOODSENSE_GITLEAKS_LOG_OPTS to the
    pull request range or the pushed range. Unset means the checked-out ref.
    """
    if explicit is not None:
        return explicit
    configured = os.environ.get("FLOODSENSE_GITLEAKS_LOG_OPTS", "").strip()
    if configured:
        return configured
    return "HEAD"


def lint_commands(
    root: Path,
    *,
    node: str,
    gitleaks: str | None,
    gitleaks_log_opts: str = "HEAD",
) -> list[tuple[Path, list[str]]]:
    """Argument lists for ruff, tsc, and gitleaks. No shell."""
    tsc = typescript_bin(root)
    exe = sys.executable
    commands: list[tuple[Path, list[str]]] = []
    if gitleaks:
        commands.append(
            (
                root,
                [
                    gitleaks,
                    "detect",
                    "--source",
                    str(root),
                    "--redact",
                    "--no-banner",
                    "--log-opts",
                    gitleaks_log_opts,
                ],
            )
        )
    commands.append((root, [exe, "-m", "ruff", "check"]))
    commands.append(
        (root, [node, str(tsc), "--noEmit", "-p", str(root / "ui" / "tsconfig.json")])
    )
    commands.append(
        (
            root,
            [node, str(tsc), "--noEmit", "-p", str(root / "contracts" / "tsconfig.json")],
        )
    )
    return commands


def _gitleaks_required(flag: bool | None) -> bool:
    if flag is None:
        return os.environ.get("FLOODSENSE_REQUIRE_GITLEAKS") == "1"
    return flag


def cmd_fetch_rag_corpus(root: Path) -> int:
    """Check corpus sha256 and download placement fetch. Does not embed."""
    path = Path(__file__).resolve().parent / "scripts" / "rag_corpus.py"
    spec = importlib.util.spec_from_file_location("rag_corpus", path)
    if spec is None or spec.loader is None:
        print("scripts/rag_corpus.py is missing", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fetch_rag_corpus(root)


def cmd_lint(
    root: Path,
    runner: Runner,
    *,
    node: str | None = None,
    gitleaks: str | None = None,
    resolve_tools: bool = True,
    require_gitleaks: bool | None = None,
    gitleaks_log_opts: str | None = None,
) -> int:
    """Tracked-env check, ruff, and TypeScript. Gitleaks runs when it is on PATH.

    CI sets FLOODSENSE_REQUIRE_GITLEAKS=1 so a missing scanner fails the job.
    Locally a missing scanner prints one line and the rest of lint still runs.
    The scan passes `--log-opts` from FLOODSENSE_GITLEAKS_LOG_OPTS, or `HEAD`
    when that variable is unset, so other fetched branches are not scanned.
    """
    code = check_tracked_env(root)
    if code != 0:
        return code
    if resolve_tools:
        if node is None:
            node = shutil.which("node")
        if gitleaks is None:
            gitleaks = shutil.which("gitleaks")
    if _gitleaks_required(require_gitleaks) and not gitleaks:
        print(
            "gitleaks is required (FLOODSENSE_REQUIRE_GITLEAKS=1) but it is not on PATH.",
            file=sys.stderr,
        )
        return 1
    if not gitleaks:
        print("gitleaks not on PATH; CI runs the secret scan. Install is optional.")
    tsc = typescript_bin(root)
    if not tsc.is_file():
        print("TypeScript is not installed. From the ui directory, run:", file=sys.stderr)
        print("  npm ci", file=sys.stderr)
        return 1
    if not node:
        print(
            "node is not on PATH. Install Node.js 20, then run npm ci in ui/.",
            file=sys.stderr,
        )
        return 1
    log_opts = resolve_gitleaks_log_opts(gitleaks_log_opts)
    for cwd, argv in lint_commands(
        root, node=node, gitleaks=gitleaks, gitleaks_log_opts=log_opts
    ):
        code = runner(argv, cwd)
        if code != 0:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tasks.py",
        description=(
            "FloodSense EU tasks for Windows, macOS, and Linux. "
            "Docker commands pin project floodsense-app."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-env", help="Copy each missing .env.example to .env. Never overwrites.")
    sub.add_parser("check-env", help="Exit 1 if api/.env, agents/.env, or ui/.env is missing.")
    sub.add_parser("up", help="Build and start API, agents, and UI. Does not start Zetaris.")
    sub.add_parser("up-all", help="up, plus the rag (pgvector) and cache (Redis) profiles.")
    sub.add_parser("down", help="Stop this project, including optional profiles. Keeps volumes.")
    sub.add_parser("config", help="Render the compose file. Prints secrets if .env is filled.")
    sub.add_parser("zetaris-sync", help="Apply pending Zetaris migrations, then verify declared views.")
    pegel = sub.add_parser(
        "pegel-poll",
        help="Fetch current PEGELONLINE levels, write the CSV, copy it into the Zetaris driver.",
    )
    pegel.add_argument("--interval", type=int, default=0, help="repeat every N seconds (600-900)")
    pegel.add_argument("--no-stage", action="store_true", help="write the CSV only")
    sub.add_parser(
        "fetch-rag-corpus",
        help=(
            "Check corpus sha256. Download placement fetch into corpus/fetched/. "
            "Does not embed and does not start Docker."
        ),
    )
    sub.add_parser("test", help="Compile and run unit tests with this interpreter.")
    sub.add_parser(
        "engines-test",
        help="npm test and npm run conformance in engines/. Needs Node.js 22.18 or newer.",
    )
    sub.add_parser(
        "lint",
        help=(
            "Tracked-.env check, ruff, and TypeScript. "
            "Gitleaks, when it is on PATH, scans the checked-out ref "
            "(or FLOODSENSE_GITLEAKS_LOG_OPTS)."
        ),
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    root: Path | None = None,
    runner: Runner | None = None,
) -> int:
    root = ROOT if root is None else root
    run = execute if runner is None else runner
    args = build_parser().parse_args(argv)
    command = args.command
    if command == "init-env":
        return init_env(root)
    if command == "check-env":
        return check_env(root)
    if command == "up":
        return cmd_up(root, run)
    if command == "up-all":
        return cmd_up_all(root, run)
    if command == "down":
        return cmd_down(root, run)
    if command == "config":
        return cmd_config(root, run)
    if command == "pegel-poll":
        extra = ["--interval", str(args.interval)] if args.interval else []
        return cmd_pegel_poll(root, run, extra + (["--no-stage"] if args.no_stage else []))
    if command == "zetaris-sync":
        return cmd_zetaris_sync(root, run)
    if command == "fetch-rag-corpus":
        return cmd_fetch_rag_corpus(root)
    if command == "test":
        return cmd_test(root, run)
    if command == "engines-test":
        return cmd_engines_test(root, run)
    if command == "lint":
        return cmd_lint(root, run)
    print(f"Unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
