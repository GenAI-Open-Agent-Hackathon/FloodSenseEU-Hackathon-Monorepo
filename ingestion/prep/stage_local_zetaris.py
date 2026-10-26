"""Copy the prep CSVs into a local Zetaris container so migration 010 can read them.

Zetaris FILESTORE paths point inside the container, not at files on the laptop.
`zetaris/migrations/010_seed_sources.sql` reads each table from a directory:

    file:///home/zetaris/customer-data/shared/floodsense_seed/<table>

This script copies `<table>.csv` to:

    /home/zetaris/customer-data/shared/floodsense_seed/<table>/<table>.csv

Run it on a cold laptop after Zetaris is up and before `zetaris-sync`. Staging
comes before registration. Migrations 010, 033, and 036 infer FILESTORE columns
at CREATE time. It also creates header-only files under floodsense_live/<table>
for every live table except DWD, so those creates do not need an AEMET pull and
do not store DWD. Those files are placeholders, not observations. 036 registers
new table names on these paths because 033's names were created before the files
existed and cannot be dropped. The container is the first argument, otherwise
`ZETARIS_CONTAINER` from the environment or `ingestion/.env`, otherwise the
same default `zetaris_sync.py` uses (`zetaris-driver-1`).

    cp ingestion/.env.example ingestion/.env   # then set ZETARIS_API_KEY only
    python ingestion/prep/stage_local_zetaris.py [container]
    python tasks.py zetaris-sync               # apply, then verify; no AEMET key, no DWD
    python scripts/zetaris_sync.py verify

Windows, from the repo root:

    .\\.venv\\Scripts\\python.exe ingestion\\prep\\stage_local_zetaris.py
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from zetaris_sync import DEFAULT_CONTAINER, load_env_file  # noqa: E402
TABLES = ["ems_footprint", "osm_sites", "portfolio_synthetic", "provenance", "valencia_points"]
DEST = "/home/zetaris/customer-data/shared/floodsense_seed"
LIVE_DEST = "/home/zetaris/customer-data/shared/floodsense_live"
# Header-only placeholders. Not observations. No dwd_rain_hourly while DWD is Hold.
# 036 CREATE must run after these files exist. Same directory names as 033.
LIVE_HEADERS = {
    "discharge_daily": (
        "point_id,date,river_discharge,river_discharge_mean,river_discharge_max,"
        "is_forecast,dataset_id,fetched_at"
    ),
    "rain_hourly": "point_id,time,precipitation_mm,is_forecast,dataset_id,fetched_at",
    "ems_activations": (
        "code,name,category,event_time,activation_time,closed,report_link,gdacs_id,"
        "dataset_id,fetched_at"
    ),
    "aemet_daily": (
        "station_id,station,date,precip_mm,tmean_c,tmin_c,tmax_c,gust_ms,dataset_id,fetched_at"
    ),
    "pegel_levels": "station,water,time,level,unit,dataset_id,fetched_at",
}


def docker(*args):
    # MSYS_NO_PATHCONV stops Git Bash rewriting the /home/... paths.
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    subprocess.run(["docker", *args], check=True, env=env)


def container_name(argv: list[str] | None = None) -> str:
    """Argument, then ZETARIS_CONTAINER, then the sync tool's default.

    Process environment wins over ingestion/.env, matching zetaris_sync.py.
    """
    args = list(sys.argv if argv is None else argv)
    if len(args) > 1 and args[1]:
        return args[1]
    file_env = load_env_file(Path(HERE).resolve().parent / ".env")
    if os.environ.get("ZETARIS_CONTAINER"):
        file_env["ZETARIS_CONTAINER"] = os.environ["ZETARIS_CONTAINER"]
    return file_env.get("ZETARIS_CONTAINER") or DEFAULT_CONTAINER


def main():
    container = container_name()
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
            # docker cp overwrites a seed CSV already in the container.
            docker("cp", os.path.join(HERE, f"{t}.csv"), f"{container}:{DEST}/{t}/{t}.csv")
        for table, header in LIVE_HEADERS.items():
            remote = f"{LIVE_DEST}/{table}"
            docker("exec", "-u", "0", container, "mkdir", "-p", remote)
            # Keep a real pull's csv. Write a header only when the directory has none.
            script = (
                f"if ! ls {remote}/*.csv >/dev/null 2>&1; then "
                f"printf '%s\\n' '{header}' > {remote}/live.csv; "
                f"fi"
            )
            docker("exec", "-u", "0", container, "bash", "-c", script)
        docker(
            "exec",
            "-u",
            "0",
            container,
            "bash",
            "-c",
            f"chmod -R a+rX {DEST} {LIVE_DEST}; chgrp -R 1001 {DEST} {LIVE_DEST}; "
            f"chmod -R g+rwX {DEST} {LIVE_DEST}",
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
    print(f"staged {len(TABLES)} seed tables in {container}:{DEST}")
    print(
        f"header-only live dirs in {container}:{LIVE_DEST} "
        f"({', '.join(LIVE_HEADERS)}; no DWD, no AEMET pull)"
    )
    print("next: python tasks.py zetaris-sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
