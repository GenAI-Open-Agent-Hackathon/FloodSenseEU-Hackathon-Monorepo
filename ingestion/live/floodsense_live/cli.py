"""Command line. One process, no shell, so PowerShell 5 can run it."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from floodsense_live.config import Config, ConfigError, load_env_file
from floodsense_live.http import ParseJsonError, PegelClient, TransportError, UrllibTransport
from floodsense_live.poller import PollError, PollResult, poll_once
from floodsense_live.postgres import PostgresGaugeStore
from floodsense_live.store import GaugeStore, InMemoryGaugeStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m floodsense_live",
        description="Poll PEGELONLINE and upsert live.gauge_* in Postgres.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch one cycle and exit. Use this for a cron tick or a smoke test.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse, but keep rows in memory. Does not open Postgres.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Env file to read. Defaults to ingestion/live/.env. Does not override.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(args.env_file)
    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    client = PegelClient(
        UrllibTransport(),
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
        backoff_seconds=config.backoff_seconds,
        user_agent=config.user_agent,
    )
    store: GaugeStore
    if args.dry_run:
        store = InMemoryGaugeStore()
    else:
        store = PostgresGaugeStore(config)
    try:
        while True:
            result = poll_once(config, client, store, pause=time.sleep)
            _print_result(result)
            if args.once:
                return 0
            time.sleep(config.interval_seconds)
    except KeyboardInterrupt:
        return 0
    except (PollError, TransportError, ParseJsonError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        if type(exc).__module__.split(".")[0] == "psycopg":
            print(f"Postgres error: {exc}", file=sys.stderr)
            print(
                "Is the database up on "
                f"{config.pg_host}:{config.pg_port}? "
                "From the repo root: python tasks.py up-db",
                file=sys.stderr,
            )
            return 1
        raise


def _print_result(result: PollResult) -> None:
    print(
        f"stations={result.stations_upserted} "
        f"measurements={result.measurements_upserted} "
        f"not_modified={result.not_modified} "
        f"requests={result.requests}"
    )
    for sample in result.samples or []:
        stamp = sample.ts_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(
            f"sample {sample.shortname} {sample.timeseries} {stamp} value={sample.value}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
