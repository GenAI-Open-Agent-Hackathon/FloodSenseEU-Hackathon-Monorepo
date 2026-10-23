"""Copy the prep CSVs into a local Zetaris driver container so migration 010 can read them.

Zetaris cannot read files on a laptop, only files inside its own volume. This stages each CSV at
/home/zetaris/customer-data/shared/floodsense_seed/<table>/<table>.csv. Run it before
`zetaris-sync` applies zetaris/migrations/010_seed_sources.sql. Local stack only.

Run from the repo root:  .venv/Scripts/python.exe ingestion/prep/stage_local_zetaris.py [container]
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
    for t in TABLES:
        docker("exec", "-u", "0", container, "mkdir", "-p", f"{DEST}/{t}")
        docker("cp", os.path.join(HERE, f"{t}.csv"), f"{container}:{DEST}/{t}/{t}.csv")
    docker("exec", "-u", "0", container, "bash", "-c",
           f"chmod -R a+rX {DEST}; chgrp -R 1001 {DEST}; chmod -R g+rwX {DEST}")
    print(f"staged {len(TABLES)} tables in {container}:{DEST}")


if __name__ == "__main__":
    main()
