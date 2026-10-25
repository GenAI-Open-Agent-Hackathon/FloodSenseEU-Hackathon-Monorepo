"""Copy the prep CSVs into a local Zetaris container so migration 010 can read them.

Zetaris FILESTORE paths point inside the container, not at files on the laptop.
`zetaris/migrations/010_seed_sources.sql` reads each table from a directory:

    file:///home/zetaris/customer-data/shared/floodsense_seed/<table>

This script copies `<table>.csv` to:

    /home/zetaris/customer-data/shared/floodsense_seed/<table>/<table>.csv

Run it on a cold laptop after Zetaris is up and before `zetaris-sync` applies 010.
Default container is `zetaris-driver-1`. If `docker ps` shows another name, pass it.

    cp ingestion/.env.example ingestion/.env   # then set ZETARIS_API_KEY
    python ingestion/prep/stage_local_zetaris.py [container]
    python tasks.py zetaris-sync               # apply, then verify declared views
    python scripts/zetaris_sync.py verify      # same checks, on their own

Windows, from the repo root:

    .\\.venv\\Scripts\\python.exe ingestion\\prep\\stage_local_zetaris.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = ["ems_footprint", "osm_sites", "portfolio_synthetic", "provenance", "valencia_points"]
DEST = "/home/zetaris/customer-data/shared/floodsense_seed"


def docker(*args):
    # MSYS_NO_PATHCONV stops Git Bash rewriting the /home/... paths.
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    subprocess.run(["docker", *args], check=True, env=env)


def main():
    container = sys.argv[1] if len(sys.argv) > 1 else "zetaris-driver-1"
    missing = [f"{t}.csv" for t in TABLES if not os.path.isfile(os.path.join(HERE, f"{t}.csv"))]
    if missing:
        print(
            "error: missing CSV(s) next to this script: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 1
    try:
        for t in TABLES:
            docker("exec", "-u", "0", container, "mkdir", "-p", f"{DEST}/{t}")
            docker("cp", os.path.join(HERE, f"{t}.csv"), f"{container}:{DEST}/{t}/{t}.csv")
        docker(
            "exec",
            "-u",
            "0",
            container,
            "bash",
            "-c",
            f"chmod -R a+rX {DEST}; chgrp -R 1001 {DEST}; chmod -R g+rwX {DEST}",
        )
    except FileNotFoundError:
        print("error: docker is not on PATH. Start Docker, then re-run.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(
            f"error: docker failed (exit {error.returncode}). "
            f"Is container '{container}' running? Check `docker ps` and pass that name.",
            file=sys.stderr,
        )
        return error.returncode or 1
    print(f"staged {len(TABLES)} tables in {container}:{DEST}")
    print("next: python tasks.py zetaris-sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
