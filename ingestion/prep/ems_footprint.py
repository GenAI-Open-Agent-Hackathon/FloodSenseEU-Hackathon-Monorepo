"""Summarise the downloaded EMSR773 observed-event layers and test the Valencia points.

Reads ingestion/raw/ems/*/*observedEventA*.json (git-ignored downloads). Writes
two small, committable files next to this script:

  ems_footprint.csv       one row per product layer: area, bbox, source URL
  valencia_points.csv     rewritten with in_flood and dist_m_to_flood filled in

Run from the repo root:  .venv/Scripts/python.exe ingestion/prep/ems_footprint.py
"""
import csv
import glob
import json
import math
import os
import re

from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw", "ems")
BASE = "https://rapidmapping.emergency.copernicus.eu/backend/EMSR773"
M_PER_DEG_LAT = 111_320.0


def load_layers():
    for path in sorted(glob.glob(os.path.join(RAW, "*", "*observedEventA*.json"))):
        name = os.path.basename(os.path.dirname(path))
        m = re.match(r"EMSR773_(AOI\d+)_(DEL|GRA)_(PRODUCT|MONIT\d+)_v(\d+)", name)
        with open(path, encoding="utf-8") as f:
            feats = json.load(f)["features"]
        geoms = [shape(x["geometry"]) for x in feats if x.get("geometry")]
        yield name, m.groups(), geoms


def area_ha(geom):
    """Approximate hectares for a WGS84 geometry near Valencia (lat ~39.4)."""
    lat = geom.centroid.y
    sx = M_PER_DEG_LAT * math.cos(math.radians(lat))
    return geom.area * sx * M_PER_DEG_LAT / 10_000


def main():
    points = list(csv.DictReader(open(os.path.join(HERE, "valencia_points.csv"), encoding="utf-8")))
    rows, all_geoms = [], []
    for name, (aoi, kind, prod, ver), geoms in load_layers():
        merged = unary_union(geoms)
        minx, miny, maxx, maxy = merged.bounds
        rows.append({
            "layer": name, "aoi": aoi, "product_type": kind, "product": prod, "version": ver,
            "features": len(geoms), "flooded_ha": round(sum(area_ha(g) for g in geoms), 1),
            "bbox_w": round(minx, 5), "bbox_s": round(miny, 5), "bbox_e": round(maxx, 5), "bbox_n": round(maxy, 5),
            "source_url": f"{BASE}/{aoi}/{kind}_{prod}/EMSR773_{aoi}_{kind}_{prod}_v{ver}.zip",
        })
        all_geoms.extend(geoms)
    with open(os.path.join(HERE, "ems_footprint.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    tree = STRtree(all_geoms)
    for p in points:
        pt = Point(float(p["lon"]), float(p["lat"]))
        idx = tree.nearest(pt)
        d_deg = pt.distance(all_geoms[idx])
        sx = M_PER_DEG_LAT * math.cos(math.radians(pt.y))
        d_m = d_deg * (sx + M_PER_DEG_LAT) / 2
        inside = any(all_geoms[i].contains(pt) for i in tree.query(pt))
        p["in_flood"] = "yes" if inside else "no"
        p["dist_m_to_flood"] = "0" if inside else str(round(d_m))
        p["verified_against_footprint"] = "yes"
    fields = ["point_id", "name", "municipality", "lat", "lon", "why", "verified_against_footprint", "in_flood", "dist_m_to_flood"]
    with open(os.path.join(HERE, "valencia_points.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(points)
    for p in points:
        print(p["point_id"], p["municipality"], p["in_flood"], p["dist_m_to_flood"])
    print(f"{len(rows)} layers, {sum(r['flooded_ha'] for r in rows):.0f} ha")


if __name__ == "__main__":
    main()
