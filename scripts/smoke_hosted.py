"""Smoke test for the hosted demo (stdlib only).

    python scripts/smoke_hosted.py http://VM_IP --user judge --password SECRET

Checks: proxy liveness, login required, API health, backend is nebius, UI served, a
question answers, operator switch blocked. Exit 0 = all passed.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request

QUESTION = "What is the current river level at Köln and is it rising?"


def call(url, auth=None, body=None, timeout=180):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode())
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except OSError as e:
        return 0, str(e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--user", default="judge")
    ap.add_argument("--password", required=True)
    ap.add_argument("--question", default=QUESTION)
    a = ap.parse_args()
    base, auth = a.base.rstrip("/"), f"{a.user}:{a.password}"
    failed = 0

    def check(name, ok, detail=""):
        nonlocal failed
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200])

    s, _ = call(f"{base}/healthz")
    check("proxy /healthz", s == 200, s)
    s, _ = call(f"{base}/api/health")
    check("login required (no credentials -> 401)", s == 401, s)
    s, b = call(f"{base}/api/health", auth)
    check("api health", s == 200 and '"ok"' in b, s)
    s, b = call(f"{base}/api/config", auth)
    try:
        backend = json.loads(b).get("llm_backend")
    except ValueError:
        backend = None
    check("llm_backend == nebius", s == 200 and backend == "nebius", backend)
    s, _ = call(f"{base}/", auth)
    check("UI served", s == 200, s)
    s, b = call(f"{base}/api/runs", auth, {"question": a.question})
    try:
        d = json.loads(b)
    except ValueError:
        d = {}
    ok = s in (200, 201) and isinstance(d, dict) and not d.get("detail")
    check("question answered", ok,
          f"{s} lane={d.get('lane')} served_from={d.get('served_from')} kind={d.get('kind')}")
    if s == 429:
        print("NOTE  429 = rate limit working; wait a minute and retry")
    s, _ = call(f"{base}/api/watch/auto-assess", auth, {"enabled": True})
    check("operator switch blocked at proxy", s == 403, s)
    print("ALL PASS" if not failed else f"{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
