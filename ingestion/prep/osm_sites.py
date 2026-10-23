"""Turn the raw Overpass extract into a flat sites table, tagged against the EMSR773 footprint.

Input : ingestion/raw/osm_valencia.json (git-ignored; query in raw/osm_query.txt, copy in prep/osm_query.overpassql)
Output: ingestion/prep/osm_sites.csv

Attribution: (c) OpenStreetMap contributors, ODbL 1.0.
Run from the repo root:  .venv/Scripts/python.exe ingestion/prep/osm_sites.py
"""
import csv
import glob
import json
import os

from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")


def site_type(tags):
    if tags.get("amenity") in ("hospital", "clinic"):
        return "health"
    if tags.get("amenity") == "school":
        return "school"
    if tags.get("amenity") in ("fire_station", "police"):
        return "emergency"
    if tags.get("shop") in ("supermarket", "mall") or tags.get("building") in ("retail", "commercial"):
        return "retail"
    return "industrial"


def main():
    with open(os.path.join(RAW, "osm_valencia.json"), encoding="utf-8") as f:
        elements = json.load(f)["elements"]
    geoms = []
    # Use the Horta Sud delineation (AOI03) plus Valencia province: the bbox of the query sits inside both.
    for path in glob.glob(os.path.join(RAW, "ems", "*AOI0[13]_DEL*", "*observedEventA*.json")):
        with open(path, encoding="utf-8") as f:
            geoms += [shape(x["geometry"]) for x in json.load(f)["features"] if x.get("geometry")]
    flood = prep(unary_union(geoms))

    rows = []
    for e in elements:
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None:
            continue
        t = e.get("tags", {})
        rows.append({
            "site_id": f"osm_{e['type'][0]}{e['id']}",
            "osm_type": e["type"], "osm_id": e["id"],
            "name": t.get("name", ""),
            "site_type": site_type(t),
            "lat": round(lat, 6), "lon": round(lon, 6),
            "in_flood_footprint": "yes" if flood.contains(Point(lon, lat)) else "no",
        })
    rows.sort(key=lambda r: r["site_id"])
    with open(os.path.join(HERE, "osm_sites.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(len(rows), "sites;", dict(Counter((r["site_type"], r["in_flood_footprint"]) for r in rows)))


if __name__ == "__main__":
    main()
