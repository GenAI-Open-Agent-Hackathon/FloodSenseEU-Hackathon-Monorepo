"""HTTP fetch with gzip, ETag, and retries. The transport is injectable."""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

Json = Any
Sleeper = Callable[[float], None]
Jitter = Callable[[], float]


class TransportError(OSError):
    """The request did not get an HTTP status (DNS, timeout, reset)."""


class HttpError(RuntimeError):
    """PEGELONLINE answered with a status this poller will not store."""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.url = url


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    url: str

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())


class Transport(Protocol):
    def request(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> HttpResponse: ...


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    not_modified: bool
    etag: str | None
    payload: Json


class UrllibTransport:
    """Standard-library GET. Sends the headers it is given, including gzip."""

    def request(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> HttpResponse:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return _from_urllib(response, url)
        except urllib.error.HTTPError as exc:
            return _from_urllib(exc, url)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError(str(exc)) from exc


def _from_urllib(response: Any, url: str) -> HttpResponse:
    raw_headers = getattr(response, "headers", {})
    headers = {key.lower(): value for key, value in raw_headers.items()}
    status = int(getattr(response, "status", getattr(response, "code", 0)))
    body = response.read()
    return HttpResponse(status=status, headers=headers, body=body, url=url)


class PegelClient:
    def __init__(
        self,
        transport: Transport,
        *,
        timeout: float,
        max_retries: int,
        backoff_seconds: float,
        user_agent: str,
        sleeper: Sleeper | None = None,
        jitter: Jitter | None = None,
    ) -> None:
        self.transport = transport
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.user_agent = user_agent
        self.sleeper = time.sleep if sleeper is None else sleeper
        self.jitter = (lambda: 0.0) if jitter is None else jitter

    def fetch_json(self, url: str, *, etag: str | None = None) -> FetchResult:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": self.user_agent,
        }
        if etag:
            headers["If-None-Match"] = etag
        delay = self.backoff_seconds
        last_status = 0
        for attempt in range(self.max_retries + 1):
            try:
                response = self.transport.request(url, headers, self.timeout)
            except TransportError:
                if attempt >= self.max_retries:
                    raise
                self._sleep(delay)
                delay = self._next_delay(delay)
                continue
            last_status = response.status
            if response.status == 304:
                return FetchResult(
                    url=url,
                    status=304,
                    not_modified=True,
                    etag=response.header("etag") or etag,
                    payload=None,
                )
            if response.status == 200:
                return FetchResult(
                    url=url,
                    status=200,
                    not_modified=False,
                    etag=response.header("etag"),
                    payload=_decode_json(response),
                )
            if response.status in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                retry_after = _retry_after(response.header("retry-after"))
                self._sleep(delay if retry_after is None else retry_after)
                delay = self._next_delay(delay)
                continue
            raise HttpError(response.status, url)
        raise HttpError(last_status, url)

    def _sleep(self, delay: float) -> None:
        if delay > 0:
            self.sleeper(min(delay, 30.0))

    def _next_delay(self, delay: float) -> float:
        bumped = delay * 2 if delay else self.backoff_seconds
        spread = 0.2 * bumped * self.jitter()
        return min(bumped + spread, 30.0)


def _decode_json(response: HttpResponse) -> Json:
    body = response.body
    if body.startswith(b"\x1f\x8b"):
        try:
            body = gzip.decompress(body)
        except OSError as exc:
            raise HttpError(response.status, response.url) from exc
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ParseJsonError(response.url) from exc


class ParseJsonError(ValueError):
    """The HTTP body was not JSON."""

    def __init__(self, url: str) -> None:
        super().__init__(f"response was not JSON: {url}")
        self.url = url


def _retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    if seconds < 0:
        return None
    return min(seconds, 30.0)
