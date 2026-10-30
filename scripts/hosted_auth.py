"""Make the judge login for the hosted demo. Prints the lines for deploy/hosted/hosted.env.

    python scripts/hosted_auth.py [--user judge] [--password SECRET]

The bcrypt hash comes from Caddy itself (needs docker). Share the plain password with
judges out of band; only the hash goes in the env file.
"""
from __future__ import annotations

import argparse
import secrets
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="judge")
    ap.add_argument("--password", default=None, help="default: random")
    a = ap.parse_args()
    password = a.password or secrets.token_urlsafe(12)
    out = subprocess.run(
        ["docker", "run", "--rm", "-i", "caddy:2-alpine", "caddy", "hash-password"],
        input=password + "\n", capture_output=True, text=True,  # stdin: not visible in `ps`
    )
    h = out.stdout.strip()
    if out.returncode != 0 or not h.startswith("$2"):
        print(out.stderr or "caddy hash-password failed", file=sys.stderr)
        return 1
    print(f"# password for judges (do not commit): {password}")
    print(f"JUDGE_USER={a.user}")
    print(f"JUDGE_HASH='{h}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
