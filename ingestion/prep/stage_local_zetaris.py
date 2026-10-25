"""Copy the prep CSVs into a local Zetaris container so migration 010 can read them.

Zetaris FILESTORE paths point inside the container, not at files on the laptop.
`zetaris/migrations/010_seed_sources.sql` reads each table from a directory:

    file:///home/zetaris/customer-data/shared/floodsense_seed/<table>

This script copies `<table>.csv` to:

    /home/zetaris/customer-data/shared/floodsense_seed/<table>/<table>.csv

Run it on a cold laptop after Zetaris is up and before `zetaris-sync`. It also
creates header-only files under floodsense_live/<table> for every 033 table except
DWD, so migration 033 can CREATE without an AEMET pull and without storing DWD.
Those files are placeholders, not observations. Default container is
`zetaris-driver-1`. If `docker ps` shows another name, pass it.

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

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = ["ems_footprint", "osm_sites", "portfolio_synthetic", "provenance", "valencia_points"]
DEST = "/home/zetaris/customer-data/shared/floodsense_seed"
LIVE_DEST = "/home/zetaris/customer-data/shared/floodsense_live"
# Header-only placeholders for 033. Not observations. No dwd_rain_hourly while DWD is Hold.
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
