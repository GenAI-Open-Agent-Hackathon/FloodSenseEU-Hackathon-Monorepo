"""Poll current PEGELONLINE water levels for a fixed station list. Zetaris serves the CSV.

  python tasks.py pegel-poll                 # one poll, write the CSV, copy it into the Zetaris driver
  python tasks.py pegel-poll --interval 600  # repeat every 10 minutes
  python ingestion/feeds/pegel_poll.py --no-stage   # write the CSV only

Writes ingestion/raw/live/pegel_now/live.csv (git-ignored), one row per station, and with
--stage (default) copies it to <container>:/home/zetaris/customer-data/shared/floodsense_live/pegel_now/
where the FILESTORE table pegel_now_src (migration 045) reads it. floodsense.gauge_levels (046)
selects from that table. Agents and UI read the view through Zetaris only.

The Ahr is not on PEGELONLINE. Its gauges (Altenahr, Bad Bodendorf) belong to the
Rhineland-Palatinate state service, not the WSV, so the Ahr stays in replay only.

Data: PEGELONLINE, WSV. Licence DL-DE->Zero-2.0. Attribution: Quelle: WSV, PEGELONLINE.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "raw", "live", "pegel_now")
DEST = "/home/zetaris/customer-data/shared/floodsense_live/pegel_now"
UA = "FloodSenseEU-hackathon/0.1 (non-commercial)"
SOURCE = "ds_pegelonline"

# PEGELONLINE shortnames. Rhine, upstream to downstream, then the Mosel.
STATIONS = (
    "MAINZ", "KAUB", "KOBLENZ", "ANDERNACH", "BONN", "KÖLN", "DÜSSELDORF",
    "Trier UP", "Cochem",
)

COLUMNS = [
    "station", "water", "ts_utc", "level_cm", "source",
    "river_km", "lat", "lon", "trend_cm_h",
    "mnw_cm", "mw_cm", "mhw_cm", "hhw_cm", "hsw_cm",
    "band", "fetched_at",
]

# near: within this share of the MW..MHW span below MHW.
NEAR_SHARE = 0.25


def fetch_json(url: str, params: dict | None = None, timeout: int = 30):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def trend_cm_h(measurements: list[dict]) -> float | None:
    """cm per hour between the newest reading and the one about an hour before it."""
    pts = sorted((utc(m["timestamp"]), float(m["value"])) for m in measurements if m.get("value") is not None)
    if len(pts) < 2:
        return None
    t1, v1 = pts[-1]
    target = t1 - timedelta(hours=1)
    t0, v0 = min(pts[:-1], key=lambda p: abs((p[0] - target).total_seconds()))
    hours = (t1 - t0).total_seconds() / 3600
    return round((v1 - v0) / hours, 1) if hours > 0 else None


def band(level: float | None, mw: float | None, mhw: float | None) -> str:
    """below / near / above against MHW (mean high water). unknown without a level or MHW."""
    if level is None or mhw is None:
        return "unknown"
    if level >= mhw:
        return "above"
    floor = mhw - NEAR_SHARE * (mhw - mw) if mw is not None and mw < mhw else mhw * (1 - NEAR_SHARE)
    return "near" if level >= floor else "below"


def station_row(name: str, fetched: str, get=fetch_json) -> list:
    quoted = urllib.parse.quote(name)
    s = get(f"{BASE}/stations/{quoted}.json", {
        "includeTimeseries": "true", "includeCurrentMeasurement": "true",
        "includeCharacteristicValues": "true",
    })
    ts = next(t for t in s.get("timeseries", []) if t.get("shortname") == "W")
    cur = ts.get("currentMeasurement") or {}
    cvals = {c["shortname"]: c.get("value") for c in ts.get("characteristicValues", []) if c.get("unit") == "cm"}
    level = cur.get("value")
    level = float(level) if level is not None else None
    try:
        trend = trend_cm_h(get(f"{BASE}/stations/{quoted}/W/measurements.json", {"start": "PT3H"}))
    except Exception:  # trend is optional; the level still counts
        trend = None
    mw, mhw = cvals.get("MW"), cvals.get("MHW")
    return [
        s["shortname"], s["water"]["shortname"],
        stamp(utc(cur["timestamp"])) if cur.get("timestamp") else "",
        level, SOURCE,
        s.get("km"), s.get("latitude"), s.get("longitude"), trend,
        cvals.get("MNW"), mw, mhw, cvals.get("HHW"), cvals.get("HSW"),
        band(level, mw, mhw), fetched,
    ]


def poll(stations=STATIONS, get=fetch_json, out_dir: str = OUT) -> tuple[str, int, list[str]]:
    """Write live.csv. Keeps the last good file when every station fails."""
    fetched = stamp(datetime.now(timezone.utc))
    rows, failed = [], []
    for name in stations:
        try:
            rows.append(station_row(name, fetched, get))
        except Exception as e:
            failed.append(f"{name}: {e}")
    path = os.path.join(out_dir, "live.csv")
    if not rows:
        return path, 0, failed
    os.makedirs(out_dir, exist_ok=True)
    with open(path + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows([["" if v is None else v for v in r] for r in rows])
    os.replace(path + ".tmp", path)
    return path, len(rows), failed


def stage(path: str, container: str) -> None:
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    run = lambda *a: subprocess.run(["docker", *a], check=True, env=env)  # noqa: E731
    run("exec", "-u", "0", container, "mkdir", "-p", DEST)
    run("cp", path, f"{container}:{DEST}/live.csv")
    run("exec", "-u", "0", container, "bash", "-c", f"chmod -R a+rX {DEST}; chgrp -R 1001 {DEST}; chmod -R g+rwX {DEST}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=int, default=0, help="repeat every N seconds (600-900 suggested)")
    ap.add_argument("--no-stage", action="store_true", help="do not copy into the Zetaris container")
    ap.add_argument("--container", default=os.environ.get("ZETARIS_DRIVER_CONTAINER", "zetaris-driver-1"))
    a = ap.parse_args(argv)
    while True:
        path, n, failed = poll()
        for f in failed:
            print(f"  failed {f}", file=sys.stderr)
        print(f"pegel_now: {n} rows -> {path}")
        if n and not a.no_stage:
            try:
                stage(path, a.container)
                print(f"staged to {a.container}:{DEST}")
            except Exception as e:
                print(f"stage failed: {e}", file=sys.stderr)
                if not a.interval:
                    return 1
        if not a.interval:
            return 0 if n else 1
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
