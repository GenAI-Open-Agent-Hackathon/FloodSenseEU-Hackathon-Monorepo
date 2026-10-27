"""Poll current PEGELONLINE water levels for a fixed station list. Zetaris serves the CSV.

  python tasks.py pegel-poll                 # one poll, write the CSV, copy it into the Zetaris driver
  python tasks.py pegel-poll --interval 600  # repeat every 10 minutes
  python ingestion/feeds/pegel_poll.py --no-stage   # write the CSV only
  python ingestion/feeds/pegel_poll.py --service    # container loop: retry with backoff, state file
  python ingestion/feeds/pegel_poll.py --health     # exit 1 when the last staged copy is too old

In docker compose the service `pegel-poller` runs --service (see compose.yaml), so no host process is needed.

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
# Touched after every successful stage. --health reads its age. Not data, never copied anywhere.
STATE = os.path.join(OUT, ".last_staged")
DEFAULT_INTERVAL_S = 600
BACKOFF_BASE_S = 30
BACKOFF_CAP_S = 300

# PEGELONLINE shortnames, chosen on 2026-10-27 from the REST API: every one has a W
# timeseries with MW and MHW characteristic values. Grouped by federal waterway,
# upstream to downstream within each. 26 stations across ten rivers.
STATIONS = (
    # Rhine
    "MAXAU",
    "MAINZ",
    "KAUB",
    "KOBLENZ",
    "ANDERNACH",
    "BONN",
    "KÖLN",
    "DÜSSELDORF",
    "EMMERICH",
    # Mosel, Saar
    "Trier UP",
    "Cochem",
    "Fremersdorf",
    # Main, Neckar
    "FRANKFURT OSTHAFEN",
    "WÜRZBURG",
    "Heidelberg UP",
    "Lauffen",
    # Elbe
    "DRESDEN",
    "MAGDEBURG-STROMBRÜCKE",
    "WITTENBERGE",
    # Danube (Donau)
    "REGENSBURG EISERNE BRÜCKE",
    "PASSAU DONAU",
    # Oder
    "FRANKFURT1 (ODER)",
    "HOHENSAATEN-FINOW",
    # Weser, Ems
    "HANN.MUENDEN",
    "PORTA",
    "RHEINE UNTERSCHLEUSE",
)

COLUMNS = [
    "station",
    "water",
    "ts_utc",
    "level_cm",
    "source",
    "river_km",
    "lat",
    "lon",
    "trend_cm_h",
    "mnw_cm",
    "mw_cm",
    "mhw_cm",
    "hhw_cm",
    "hsw_cm",
    "band",
    "fetched_at",
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
    pts = sorted(
        (utc(m["timestamp"]), float(m["value"])) for m in measurements if m.get("value") is not None
    )
    if len(pts) < 2:
        return None
    t1, v1 = pts[-1]
    target = t1 - timedelta(hours=1)
    t0, v0 = min(pts[:-1], key=lambda p: abs((p[0] - target).total_seconds()))
    hours = (t1 - t0).total_seconds() / 3600
    return round((v1 - v0) / hours, 1) if hours >= 0.5 else None


def band(level: float | None, mw: float | None, mhw: float | None) -> str:
    """below / near / above against MHW (mean high water). unknown without a level or MHW."""
    if level is None or mhw is None:
        return "unknown"
    if level >= mhw:
        return "above"
    if mw is None or mw >= mhw:
        return "below"  # no usable MW: MHW only, no invented near floor
    return "near" if level >= mhw - NEAR_SHARE * (mhw - mw) else "below"


def station_row(name: str, fetched: str, get=fetch_json) -> list:
    quoted = urllib.parse.quote(name)
    s = get(
        f"{BASE}/stations/{quoted}.json",
        {
            "includeTimeseries": "true",
            "includeCurrentMeasurement": "true",
            "includeCharacteristicValues": "true",
        },
    )
    ts = next(t for t in s.get("timeseries", []) if t.get("shortname") == "W")
    cur = ts.get("currentMeasurement") or {}
    cvals = {
        c["shortname"]: c.get("value")
        for c in ts.get("characteristicValues", [])
        if c.get("unit") == "cm"
    }
    level = cur.get("value")
    level = float(level) if level is not None else None
    try:
        trend = trend_cm_h(get(f"{BASE}/stations/{quoted}/W/measurements.json", {"start": "PT3H"}))
    except Exception:  # trend is optional; the level still counts
        trend = None
    mw, mhw = cvals.get("MW"), cvals.get("MHW")
    return [
        s["shortname"],
        s["water"]["shortname"],
        stamp(utc(cur["timestamp"])) if cur.get("timestamp") else "",
        level,
        SOURCE,
        s.get("km"),
        s.get("latitude"),
        s.get("longitude"),
        trend,
        cvals.get("MNW"),
        mw,
        mhw,
        cvals.get("HHW"),
        cvals.get("HSW"),
        band(level, mw, mhw),
        fetched,
    ]


def previous_rows(path: str) -> dict[str, list]:
    """Rows of the last good file by the station name the poller asked for (or shortname)."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rd = csv.reader(f)
            if next(rd, None) != COLUMNS:
                return {}
            out = {}
            for r in rd:
                out[r[0]] = r
                out[r[0].upper()] = r
            return out
    except OSError:
        return {}


def empty_row(name: str, fetched: str) -> list:
    """Never fetched: no level, band unknown. fetched_at empty so it reads as stale, not current."""
    row = dict.fromkeys(COLUMNS)
    row.update(station=name, source=SOURCE, band="unknown")
    return [row[c] for c in COLUMNS]


def poll(stations=STATIONS, get=fetch_json, out_dir: str = OUT) -> tuple[str, int, list[str]]:
    """Write live.csv. Keeps the last good file when every station fails."""
    fetched = stamp(datetime.now(timezone.utc))
    path = os.path.join(out_dir, "live.csv")
    previous = previous_rows(path)
    rows, failed, fresh = [], [], 0
    for name in stations:
        try:
            rows.append(station_row(name, fetched, get))
            fresh += 1
        except Exception as e:
            failed.append(f"{name}: {e}")
            # Keep the station: its last row with its old fetched_at, else an empty row.
            rows.append(
                previous.get(name) or previous.get(name.upper()) or empty_row(name, fetched)
            )
    if not fresh:
        return path, 0, failed
    os.makedirs(out_dir, exist_ok=True)
    with open(path + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows([["" if v is None else v for v in r] for r in rows])
    os.replace(path + ".tmp", path)
    return path, fresh, failed


def stage(path: str, container: str) -> None:
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    run = lambda *a: subprocess.run(["docker", *a], check=True, env=env)  # noqa: E731
    run("exec", "-u", "0", container, "mkdir", "-p", DEST)
    # Dot-prefixed temp name: Spark skips hidden files, and mv in one directory is atomic.
    run("cp", path, f"{container}:{DEST}/.live.csv.tmp")
    run(
        "exec",
        "-u",
        "0",
        container,
        "bash",
        "-c",
        f"chmod a+r {DEST}/.live.csv.tmp; chgrp 1001 {DEST}/.live.csv.tmp; chmod g+rw {DEST}/.live.csv.tmp; "
        f"chmod a+rx {DEST}; mv -f {DEST}/.live.csv.tmp {DEST}/live.csv",
    )


def backoff_s(failures: int, base: int = BACKOFF_BASE_S, cap: int = BACKOFF_CAP_S) -> int:
    """Seconds to wait after the Nth consecutive failure (1-based): base, 2x, 4x ... up to cap."""
    return min(cap, base * 2 ** max(0, failures - 1))


def log(msg: str, err: bool = False) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"{ts} pegel-poller: {msg}", file=sys.stderr if err else sys.stdout, flush=True)


def cycle(container: str, poll_fn=None, stage_fn=None, mark=None) -> tuple[bool, str]:
    """One poll plus one stage. Returns (ok, one-line summary). Never raises."""
    poll_fn = poll_fn or poll
    stage_fn = stage_fn or stage
    mark = mark or mark_staged
    try:
        path, fresh, failed = poll_fn()
    except Exception as e:
        return False, f"poll crashed: {e}"
    for f in failed:
        log(f"station failed {f}", err=True)
    if not fresh:
        return False, f"polled {len(STATIONS)} stations, 0 fresh: PEGELONLINE unreachable, nothing staged"
    try:
        stage_fn(path, container)
    except Exception as e:
        return False, (
            f"polled {len(STATIONS)} stations, {fresh} fresh, but staging into {container} failed "
            f"(is the Zetaris stack up?): {e}"
        )
    mark()
    return True, f"polled {len(STATIONS)} stations, {fresh} fresh, staged to {container}:{DEST}/live.csv"


def mark_staged(path: str = STATE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(stamp(datetime.now(timezone.utc)) + "\n")


def health(interval: int, path: str = STATE, now=time.time) -> tuple[bool, str]:
    """Healthy when the last successful stage is at most 2x interval old."""
    try:
        age = now() - os.path.getmtime(path)
    except OSError:
        return False, "no successful stage yet"
    limit = 2 * interval
    return age <= limit, f"last staged {int(age)}s ago (limit {limit}s)"


def serve(
    interval: int, container: str, cycle_fn=cycle, sleep=time.sleep, max_cycles: int | None = None
) -> int:
    """Poll forever. Failures are logged on stderr and retried with backoff, never fatal."""
    failures, done = 0, 0
    log(f"start: every {interval}s, container {container}. Quelle: WSV, PEGELONLINE")
    while max_cycles is None or done < max_cycles:
        done += 1
        ok, msg = cycle_fn(container)
        if ok:
            failures = 0
            log(f"{msg}; next in {interval}s")
            wait = interval
        else:
            failures += 1
            wait = min(backoff_s(failures), interval)
            log(f"FAILED (attempt {failures}): {msg}; retry in {wait}s", err=True)
        sleep(wait)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--interval", type=int, default=0, help="repeat every N seconds (600-900 suggested)"
    )
    ap.add_argument(
        "--no-stage", action="store_true", help="do not copy into the Zetaris container"
    )
    ap.add_argument("--service", action="store_true", help="container loop with retry and backoff")
    ap.add_argument("--health", action="store_true", help="exit 1 if the last stage is >2x interval old")
    ap.add_argument(
        "--container",
        default=os.environ.get("ZETARIS_CONTAINER")
        or os.environ.get("ZETARIS_DRIVER_CONTAINER", "zetaris-driver-1"),
    )
    a = ap.parse_args(argv)
    if a.service or a.health:
        interval = a.interval or int(os.environ.get("POLL_INTERVAL_S") or DEFAULT_INTERVAL_S)
        if a.health:
            ok, msg = health(interval)
            print(msg)
            return 0 if ok else 1
        return serve(interval, a.container)
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
