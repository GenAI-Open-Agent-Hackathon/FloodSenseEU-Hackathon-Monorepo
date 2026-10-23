"""Environment for the poller. Secrets stay in the git-ignored env file."""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path

from floodsense_live.parse import DEFAULT_BASE_URL

# Official PEGELONLINE shortnames, upstream to downstream along the Rhine.
# The Ahr itself is not on this service. ANDERNACH and BONN bracket the mouth.
DEFAULT_STATIONS: tuple[str, ...] = (
    "KAUB",
    "KOBLENZ",
    "ANDERNACH",
    "BONN",
    "KÖLN",
    "DÜSSELDORF",
)

SHORTNAME_ALIASES = {
    "KOELN": "KÖLN",
    "DUESSELDORF": "DÜSSELDORF",
    "DUSSELDORF": "DÜSSELDORF",
}

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class ConfigError(ValueError):
    """An environment value is missing or not usable."""


@dataclass(frozen=True)
class Config:
    base_url: str
    stations: tuple[str, ...]
    timeseries: tuple[str, ...]
    lookback: str
    interval_seconds: int
    timeout_seconds: float
    max_retries: int
    backoff_seconds: float
    pause_seconds: float
    all_current: bool
    user_agent: str
    pg_host: str
    pg_port: int
    pg_db: str
    pg_user: str
    pg_password: str
    pg_sslmode: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        source = os.environ if env is None else env
        all_current = _bool(source.get("PEGELONLINE_ALL_CURRENT", "0"), "PEGELONLINE_ALL_CURRENT")
        stations = _stations(source.get("PEGELONLINE_STATIONS"))
        if not stations and not all_current:
            raise ConfigError("PEGELONLINE_STATIONS is empty. Set at least one gauge.")
        timeseries = _timeseries(source.get("PEGELONLINE_TIMESERIES"))
        return cls(
            base_url=_base_url(source.get("PEGELONLINE_BASE_URL", DEFAULT_BASE_URL)),
            stations=stations,
            timeseries=timeseries,
            lookback=_lookback(source.get("PEGELONLINE_LOOKBACK", "P1D")),
            interval_seconds=_int_range(
                source.get("PEGELONLINE_INTERVAL_SECONDS", "900"),
                "PEGELONLINE_INTERVAL_SECONDS",
                low=60,
                high=86400,
            ),
            timeout_seconds=float(
                _int_range(
                    source.get("PEGELONLINE_TIMEOUT_SECONDS", "20"),
                    "PEGELONLINE_TIMEOUT_SECONDS",
                    low=1,
                    high=120,
                )
            ),
            max_retries=_int_range(
                source.get("PEGELONLINE_MAX_RETRIES", "3"),
                "PEGELONLINE_MAX_RETRIES",
                low=0,
                high=8,
            ),
            backoff_seconds=float(
                _int_range(
                    source.get("PEGELONLINE_BACKOFF_SECONDS", "1"),
                    "PEGELONLINE_BACKOFF_SECONDS",
                    low=0,
                    high=60,
                )
            ),
            pause_seconds=_pause(source.get("PEGELONLINE_REQUEST_PAUSE_SECONDS", "0.25")),
            all_current=all_current,
            user_agent=source.get(
                "PEGELONLINE_USER_AGENT",
                "FloodSenseEU/0.1 (PEGELONLINE poller)",
            ).strip()
            or "FloodSenseEU/0.1 (PEGELONLINE poller)",
            pg_host=source.get("POSTGRES_HOST", "127.0.0.1").strip() or "127.0.0.1",
            pg_port=_int_range(
                source.get("POSTGRES_PORT", "15432"),
                "POSTGRES_PORT",
                low=1,
                high=65535,
            ),
            pg_db=source.get("POSTGRES_DB", "floodsense").strip() or "floodsense",
            pg_user=source.get("POSTGRES_USER", "floodsense").strip() or "floodsense",
            pg_password=source.get("POSTGRES_PASSWORD", ""),
            pg_sslmode=source.get("POSTGRES_SSLMODE", "disable").strip() or "disable",
        )


def canonical_shortname(name: str) -> str:
    text = name.strip().upper()
    return SHORTNAME_ALIASES.get(text, text)


def load_env_file(
    path: Path | None = None,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> int:
    """Set keys that are not already in the environment. Never overrides.

    Returns how many keys were set. A missing file is not an error: the
    process environment is enough for CI and for `--dry-run` experiments.
    Values are not logged.
    """
    target = os.environ if environ is None else environ
    env_path = ENV_FILE if path is None else path
    if not env_path.is_file():
        return 0
    set_count = 0
    text = env_path.read_text(encoding="utf-8-sig")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in target:
            continue
        target[key] = _unquote(value.strip())
        set_count += 1
    return set_count


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _base_url(value: str) -> str:
    text = value.strip().rstrip("/")
    if not text.startswith("https://"):
        raise ConfigError("PEGELONLINE_BASE_URL must start with https://")
    return text


def _stations(value: str | None) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_STATIONS
    names = []
    seen: set[str] = set()
    for part in value.split(","):
        if not part.strip():
            continue
        name = canonical_shortname(part)
        key = name.upper()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return tuple(names)


def _timeseries(value: str | None) -> tuple[str, ...]:
    raw = "W" if value is None or not value.strip() else value
    names = []
    seen: set[str] = set()
    for part in raw.split(","):
        name = part.strip().upper()
        if not name or name in seen:
            continue
        if not name.replace("_", "").isalnum():
            raise ConfigError(f"PEGELONLINE_TIMESERIES has an unexpected name: {part!r}")
        seen.add(name)
        names.append(name)
    if not names:
        raise ConfigError("PEGELONLINE_TIMESERIES is empty")
    return tuple(names)


def _lookback(value: str) -> str:
    text = value.strip().upper()
    allowed = set("0123456789PDTHMS")
    if (
        len(text) < 2
        or len(text) > 32
        or not text.startswith("P")
        or text in {"P", "PT"}
        or any(char not in allowed for char in text)
    ):
        raise ConfigError(
            "PEGELONLINE_LOOKBACK must be an ISO-8601 duration such as P1D or PT6H"
        )
    return text


def _int_range(value: str, name: str, *, low: int, high: int) -> int:
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if parsed < low or parsed > high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return parsed


def _pause(value: str) -> float:
    try:
        parsed = float(value.strip())
    except (TypeError, ValueError) as exc:
        raise ConfigError("PEGELONLINE_REQUEST_PAUSE_SECONDS must be a number") from exc
    if parsed < 0 or parsed > 30:
        raise ConfigError("PEGELONLINE_REQUEST_PAUSE_SECONDS must be between 0 and 30")
    return parsed


def _bool(value: str, name: str) -> bool:
    text = value.strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    raise ConfigError(f"{name} must be 0 or 1")
