"""Smoke test for the hosted demo (stdlib only).

    python scripts/smoke_hosted.py http://VM_IP --user judge --password SECRET

Checks: proxy liveness, login required, API health, backend is nebius, UI served, a
small-talk reply, a full-lane event run, operator switch blocked. Self-signed proxy: --insecure. Exit 0 = all passed.
"""
from __future__ import annotations

import argparse
import base64
import json
import ssl
import sys
import urllib.error
import urllib.request

# Hosted mode is Demo data (FF_LIVE_DATA=false): the router sends every real question to the
# full lane, so ask an event question the seed data can answer. The full lane can take minutes.
QUESTION = "What happened in the Valencia flood of 29 October 2024 and which insured sites were exposed?"


CTX = None


def call(url, auth=None, body=None, timeout=900):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode())
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except OSError as e:
        return 0, str(e)


def _json(b):
    try:
        d = json.loads(b)
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--user", default="judge")
    ap.add_argument("--password", required=True)
    ap.add_argument("--question", default=QUESTION)
    ap.add_argument("--insecure", action="store_true", help="accept a self-signed certificate")
    a = ap.parse_args()
    global CTX
    if a.insecure:
        CTX = ssl._create_unverified_context()
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
    s, b = call(f"{base}/api/runs", auth, {"question": "hello"})
    d = _json(b)
    check("small talk answered (front door reply)", s == 200 and d.get("kind") == "reply", f"{s} kind={d.get('kind')}")
    s, b = call(f"{base}/api/runs", auth, {"question": a.question})
    d = _json(b)
    ok = s in (200, 201) and bool(d.get("run_id")) and d.get("lane") == "full" and bool(d.get("claims") or d.get("status"))
    check("event question ran on the full lane", ok,
          f"{s} lane={d.get('lane')} status={d.get('status')} served_from={d.get('served_from')} run_id={d.get('run_id')}")
    if s == 429:
        print("NOTE  429 = rate limit working; wait a minute and retry")
    s, _ = call(f"{base}/api/watch/auto-assess", auth, {"enabled": True})
    check("operator switch blocked at proxy", s == 403, s)
    print("ALL PASS" if not failed else f"{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
