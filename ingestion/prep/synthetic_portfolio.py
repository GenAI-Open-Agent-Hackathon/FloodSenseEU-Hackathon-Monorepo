"""Generate the SYNTHETIC insurer portfolio from the OSM sites table.

Every row is invented. No real policies, customers or personal data. The seed
is fixed, so the output is identical on every machine.

Input : ingestion/prep/osm_sites.csv
Output: ingestion/prep/portfolio_synthetic.csv

Run from the repo root:  .venv/Scripts/python.exe ingestion/prep/synthetic_portfolio.py
"""
import csv
import os
import random
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 773  # EMSR773
INSURED_TYPES = {"industrial": (400_000, 12_000_000), "retail": (150_000, 5_000_000)}
LINE = "commercial_property"


def main():
    rng = random.Random(SEED)
    sites = [r for r in csv.DictReader(open(os.path.join(HERE, "osm_sites.csv"), encoding="utf-8"))
             if r["site_type"] in INSURED_TYPES]
    sites.sort(key=lambda r: r["site_id"])
    rows = []
    for i, s in enumerate(sites, 1):
        if rng.random() > 0.8:  # not every site is insured by our fictional insurer
            continue
        lo, hi = INSURED_TYPES[s["site_type"]]
        inception = date(2024, 1, 1) + timedelta(days=rng.randrange(0, 270))
        rows.append({
            "policy_id": f"SYN-{len(rows) + 1:05d}",
            "site_id": s["site_id"],
            "insured_name": s["name"] or f"Unnamed {s['site_type']} site",
            "line": LINE,
            "sum_insured_eur": int(round(rng.uniform(lo, hi), -3)),
            "deductible_eur": rng.choice([2_500, 5_000, 10_000, 25_000]),
            "flood_cover": "yes" if rng.random() < 0.7 else "no",
            "inception": inception.isoformat(),
            "expiry": (inception + timedelta(days=365)).isoformat(),
            "synthetic": "yes",
        })
    with open(os.path.join(HERE, "portfolio_synthetic.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "synthetic policies from", len(sites), "candidate sites")


if __name__ == "__main__":
    main()
