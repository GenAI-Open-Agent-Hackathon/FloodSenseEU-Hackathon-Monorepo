"""Check every source and pull live + existing data, up to date.

  python ingestion/feeds/feeds.py check                     # reachability + newest data point per source
  python ingestion/feeds/feeds.py pull                      # default sources from --since (default 2024-10-20) to now
  python ingestion/feeds/feeds.py pull --only aemet,dwd --since 2021-07-10
  python ingestion/feeds/feeds.py pull --stage              # also copy into the local Zetaris driver container

Default check and pull skip dwd. DWD terms are Hold in docs/legal/sources.md (no full-text storage).
Opt in with --only dwd. That still does not register a Zetaris table.

Writes CSVs to ingestion/raw/live/<table>/ (git-ignored). Every row carries fetched_at. The AEMET key is read
from ingestion/.env (AEMET_API_KEY) and never printed. Licences and attribution: docs/legal/sources.md.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ING = os.path.join(HERE, "..")
PREP = os.path.join(ING, "prep")
OUT = os.path.join(ING, "raw", "live")
DEST = "/home/zetaris/customer-data/shared/floodsense_live"
UA = "FloodSenseEU-hackathon/0.1 (non-commercial)"

# Approximate town centres for the July 2021 Ahr valley (not surveyed points).
AHR = [("AHR01", "Altenahr", 50.5192, 6.9917), ("AHR02", "Bad Neuenahr-Ahrweiler", 50.5436, 7.1103),
       ("AHR03", "Schuld", 50.4896, 6.9033), ("AHR04", "Dernau", 50.5300, 7.0500)]
RHINE_GAUGES = ["BONN", "KÖLN", "KOBLENZ"]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def env(name):
    try:
        for line in open(os.path.join(ING, ".env"), encoding="utf-8"):
            m = re.match(rf"\s*{name}=(.*)", line)
            if m:
                return m[1].strip()
    except OSError:
        pass
    return os.environ.get(name, "")


def fetch(url, params=None, headers=None, data=None, timeout=40, tries=3):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})}, data=data)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:
            last = e
        time.sleep(2 ** (i + 1))
    raise last


def js(*a, **k):
    b = fetch(*a, **k)
    try:
        return json.loads(b.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(b.decode("latin-1"))


def points():
    with open(os.path.join(PREP, "valencia_points.csv"), newline="", encoding="utf-8") as f:
        return [(r["point_id"], r["lat"], r["lon"]) for r in csv.DictReader(f)]


def write(table, cols, rows, name="live"):
    d = os.path.join(OUT, table)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{name}.csv")
    with open(p + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    os.replace(p + ".tmp", p)
    print(f"  {table}: {len(rows)} rows")
    return len(rows)


def listify(x):
    return x if isinstance(x, list) else [x]


def num(s):
    s = (s or "").replace(",", ".").strip()
    try:
        return str(float(s))
    except ValueError:
        return ""


# ---------- sources: each has check() -> newest-point string and pull(since, fetched) ----------

def c_open_meteo_flood():
    d = js("https://flood-api.open-meteo.com/v1/flood", {"latitude": 39.4278, "longitude": -0.4172,
                                                         "daily": "river_discharge", "past_days": 1, "forecast_days": 7})
    return f"forecast to {d['daily']['time'][-1]}"


def p_open_meteo_flood(since, fetched):
    pts, rows = points(), []
    q = {"latitude": ",".join(p[1] for p in pts), "longitude": ",".join(p[2] for p in pts),
         "daily": "river_discharge,river_discharge_mean,river_discharge_max", "start_date": since,
         "end_date": (date.today() + timedelta(days=7)).isoformat()}
    today = date.today().isoformat()
    for p, d in zip(pts, listify(js("https://flood-api.open-meteo.com/v1/flood", q))):
        dd = d["daily"]
        for i, day in enumerate(dd["time"]):
            rows.append([p[0], day, dd["river_discharge"][i], dd["river_discharge_mean"][i], dd["river_discharge_max"][i],
                         "yes" if day > today else "no", "ds_open_meteo_flood", fetched])
    return write("discharge_daily", ["point_id", "date", "river_discharge", "river_discharge_mean",
                                      "river_discharge_max", "is_forecast", "dataset_id", "fetched_at"], rows)


def c_open_meteo_rain():
    d = js("https://api.open-meteo.com/v1/forecast", {"latitude": 39.4278, "longitude": -0.4172,
                                                       "hourly": "precipitation", "past_days": 1, "forecast_days": 3})
    return f"forecast to {d['hourly']['time'][-1]}"


def p_open_meteo_rain(since, fetched):
    pts, rows = points(), []
    geo = {"latitude": ",".join(p[1] for p in pts), "longitude": ",".join(p[2] for p in pts), "hourly": "precipitation"}
    cut = fetched[:13]
    end_arch = (date.today() - timedelta(days=5)).isoformat()  # the archive lags a few days
    for p, d in zip(pts, listify(js("https://archive-api.open-meteo.com/v1/archive", {**geo, "start_date": since, "end_date": end_arch}))):
        for t, v in zip(d["hourly"]["time"], d["hourly"]["precipitation"]):
            rows.append([p[0], t, v, "no", "ds_open_meteo_rain", fetched])
    for p, d in zip(pts, listify(js("https://api.open-meteo.com/v1/forecast", {**geo, "past_days": 6, "forecast_days": 3}))):
        for t, v in zip(d["hourly"]["time"], d["hourly"]["precipitation"]):
            if t[:10] > end_arch:
                rows.append([p[0], t, v, "yes" if t[:13] > cut else "no", "ds_open_meteo_rain", fetched])
    return write("rain_hourly", ["point_id", "time", "precipitation_mm", "is_forecast", "dataset_id", "fetched_at"], rows)


def c_ems():
    r = js("https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/", {"code": "EMSR773"})["results"][0]
    return f"EMSR773 closed={r['closed']}"


def p_ems(since, fetched):
    rows = []
    for code in ["EMSR773"]:
        for r in js("https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/", {"code": code})["results"]:
            rows.append([r["code"], r["name"], r["category"], r["eventTime"], r["activationTime"], r["closed"],
                         r.get("reportLink") or "", r.get("gdacsId") or "", "ds_ems_emsr773", fetched])
    return write("ems_activations", ["code", "name", "category", "event_time", "activation_time", "closed",
                                      "report_link", "gdacs_id", "dataset_id", "fetched_at"], rows)


def aemet(path):
    key = env("AEMET_API_KEY")
    if not key:
        raise RuntimeError("AEMET_API_KEY missing in ingestion/.env")
    r = js(f"https://opendata.aemet.es/opendata/api/{path}", headers={"api_key": key})
    if r.get("estado") != 200:
        raise RuntimeError(f"AEMET {r.get('estado')} {r.get('descripcion')}")
    return js(r["datos"])


def c_aemet():
    d = aemet("observacion/convencional/todas")
    return f"newest obs {max(e['fint'] for e in d)}"


def valencia_stations():
    inv = aemet("valores/climatologicos/inventarioestaciones/todasestaciones")
    return {e["indicativo"]: e["nombre"] for e in inv if e.get("provincia") == "VALENCIA"}


def p_aemet(since, fetched):
    st = valencia_stations()
    rows, errors, a = [], [], datetime.fromisoformat(since).date()
    end = date.today() - timedelta(days=1)
    while a <= end:
        b = min(a + timedelta(days=14), end)  # AEMET allows at most 15 days per request
        try:
            for e in aemet(f"valores/climatologicos/diarios/datos/fechaini/{a}T00:00:00UTC/fechafin/{b}T23:59:59UTC/todasestaciones"):
                if e.get("indicativo") in st:
                    rows.append([e["indicativo"], st[e["indicativo"]], e["fecha"], num(e.get("prec")), num(e.get("tmed")),
                                 num(e.get("tmin")), num(e.get("tmax")), num(e.get("racha")), "ds_aemet", fetched])
        except RuntimeError as ex:
            errors.append(f"{a}..{b}: {ex}")
        a = b + timedelta(days=1)
        time.sleep(1.5)  # stay under AEMET's rate limit
    write("aemet_daily", ["station_id", "station", "date", "precip_mm", "tmean_c", "tmin_c", "tmax_c",
                          "gust_ms", "dataset_id", "fetched_at"], rows)
    if errors:
        raise RuntimeError(f"{len(errors)} chunk(s) failed, first: {errors[0]}")
    return len(rows)


def c_dwd():
    d = js("https://api.brightsky.dev/current_weather", {"lat": AHR[0][2], "lon": AHR[0][3]})
    return f"DWD obs {d['weather']['timestamp'][:16]}"


def p_dwd(since, fetched):
    rows = []
    end = date.today().isoformat()
    for pid, name, lat, lon in AHR:
        d = js("https://api.brightsky.dev/weather", {"lat": lat, "lon": lon, "date": since, "last_date": end})
        for w in d["weather"]:
            rows.append([pid, name, w["timestamp"], w["precipitation"], "ds_dwd_brightsky", fetched])
    return write("dwd_rain_hourly", ["point_id", "name", "time", "precipitation_mm", "dataset_id", "fetched_at"], rows)


def pegel_stations():
    ss = js("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json", {"waters": "RHEIN"})
    return [s for s in ss if s["shortname"].upper() in RHINE_GAUGES]


def c_pegel():
    s = pegel_stations()[0]
    m = js(f"https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/{s['uuid']}/W/currentmeasurement.json")
    return f"{s['shortname']} {m['timestamp'][:16]}"


def p_pegel(since, fetched):
    rows = []
    for s in pegel_stations():
        for m in js(f"https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/{s['uuid']}/W/measurements.json", {"start": "P30D"}):
            rows.append([s["shortname"], s["water"]["shortname"], m["timestamp"], m["value"], "cm", "ds_pegelonline", fetched])
    return write("pegel_levels", ["station", "water", "time", "level", "unit", "dataset_id", "fetched_at"], rows)


def c_osm():
    q = "[out:json][timeout:25];node(39.4278,-0.4172,39.4279,-0.4171);out count;"
    for host in ("overpass-api.de", "overpass.kumi.systems"):
        try:
            fetch(f"https://{host}/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), timeout=60, tries=1)
            return f"overpass up ({host})"
        except Exception as e:
            err = e
    raise err


def p_osm(since, fetched):
    # Live extract goes under raw/live. Do not rewrite prep/osm_sites.csv: the 359-row
    # portfolio join is pinned to that committed file.
    q = open(os.path.join(PREP, "osm_query.overpassql"), encoding="utf-8").read()
    live_dir = os.path.join(OUT, "osm_sites")
    os.makedirs(live_dir, exist_ok=True)
    out_csv = os.path.join(live_dir, "live.csv")
    for host in ("overpass-api.de", "overpass.kumi.systems"):
        try:
            b = fetch(f"https://{host}/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), timeout=180, tries=1)
            open(os.path.join(ING, "raw", "osm_valencia.json"), "wb").write(b)
            env = {**os.environ, "FLOODSENSE_OSM_SITES_OUT": out_csv}
            subprocess.run([sys.executable, os.path.join(PREP, "osm_sites.py")], check=True, env=env)
            return 1
        except Exception as e:
            print(f"  osm via {host}: {e}", file=sys.stderr)
    raise RuntimeError("no Overpass host answered; prep/osm_sites.csv was not modified")


def c_hochwasserzentralen():
    b = fetch("https://www.hochwasserzentralen.de/webservices/get_lagepegel.php", timeout=30, tries=1)
    if not b.strip():
        raise RuntimeError("HTTP 200 but empty body (documented API not serving data)")
    return f"{len(b)} bytes"


def c_saih():
    fetch("https://saih.chj.es/", timeout=30, tries=1)
    raise RuntimeError("site up but only a web page: no documented data API or terms")


SOURCES = {
    "open_meteo_flood": (c_open_meteo_flood, p_open_meteo_flood),
    "open_meteo_rain": (c_open_meteo_rain, p_open_meteo_rain),
    "ems": (c_ems, p_ems),
    "aemet": (c_aemet, p_aemet),
    "dwd": (c_dwd, p_dwd),
    "pegelonline": (c_pegel, p_pegel),
    "osm": (c_osm, p_osm),
    "hochwasserzentralen": (c_hochwasserzentralen, None),
    "saih_jucar": (c_saih, None),
}

# Terms not cleared. Stay out of check/pull unless --only names them.
HELD_UNTIL_TERMS = frozenset({"dwd"})


def selected_sources(only):
    """Names to check or pull. None means every source except HELD_UNTIL_TERMS."""
    if only is None:
        return [name for name in SOURCES if name not in HELD_UNTIL_TERMS]
    names = [part.strip() for part in only.split(",") if part.strip()]
    unknown = [name for name in names if name not in SOURCES]
    if unknown:
        raise ValueError("unknown source: " + ", ".join(unknown))
    return names


def check(names):
    print(f"{'source':<22}{'status':<7}{'secs':<7}detail")
    bad = 0
    for n in names:
        t = time.time()
        try:
            detail, st = SOURCES[n][0](), "OK"
        except Exception as e:
            detail, st = str(e)[:90], "FAIL"
            bad += 1
        print(f"{n:<22}{st:<7}{time.time() - t:<7.1f}{detail}")
    return bad


def provenance(fetched):
    with open(os.path.join(PREP, "provenance.csv"), newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        cols, rows = rd.fieldnames, list(rd)
    kept = []
    for r in rows:
        if r["dataset_id"] == "ds_dwd_brightsky":
            continue
        if r["dataset_id"] in {"ds_open_meteo_flood", "ds_open_meteo_rain", "ds_ems_emsr773", "ds_aemet"}:
            r["accessed_at"] = fetched
        kept.append(r)
    write("provenance", cols, [[r[c] for c in cols] for r in kept], "provenance")


def stage(container):
    env_ = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    run = lambda *a: subprocess.run(["docker", *a], check=True, env=env_)  # noqa: E731
    tables = [t for t in os.listdir(OUT) if os.path.isdir(os.path.join(OUT, t))]
    for t in tables:
        run("exec", "-u", "0", container, "mkdir", "-p", f"{DEST}/{t}")
        for fn in os.listdir(os.path.join(OUT, t)):
            if fn.endswith(".csv"):
                run("cp", os.path.join(OUT, t, fn), f"{container}:{DEST}/{t}/{fn}")
    run("exec", "-u", "0", container, "bash", "-c", f"chmod -R a+rX {DEST}; chgrp -R 1001 {DEST}; chmod -R g+rwX {DEST}")
    print(f"staged {len(tables)} tables to {container}:{DEST}")


def pull(names, since, do_stage, container):
    fetched = now()
    print(f"pull since {since} @ {fetched}")
    failed = []
    for n in names:
        fn = SOURCES[n][1]
        if not fn:
            print(f"  {n}: skipped (no usable API)")
            continue
        try:
            fn(since, fetched)
        except Exception as e:
            failed.append(n)
            print(f"  {n}: FAILED, keeping last good file: {e}", file=sys.stderr)
    provenance(fetched)
    if do_stage:
        stage(container)
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "pull"])
    ap.add_argument("--only", help="comma-separated source names")
    ap.add_argument("--since", default="2024-10-20")
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--container", default="zetaris-driver-1")
    ap.add_argument("--interval", type=int, default=0, help="pull: repeat every N seconds")
    a = ap.parse_args()
    try:
        names = selected_sources(a.only)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
    if a.cmd == "check":
        sys.exit(1 if check(names) else 0)
    while True:
        failed = pull(names, a.since, a.stage, a.container)
        if not a.interval:
            sys.exit(1 if failed else 0)
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
