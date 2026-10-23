"""HTTP client tests. The transport is scripted, so CI makes no network calls."""

from __future__ import annotations

import gzip
import json
import unittest
from collections.abc import Mapping

from floodsense_live.http import (
    HttpError,
    HttpResponse,
    PegelClient,
    TransportError,
)

BONN = {"shortname": "BONN", "uuid": "593647aa-9fea-43ec-a7d6-6476a76ae868"}


class ScriptedTransport:
    def __init__(self, responses: list[HttpResponse | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def request(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> HttpResponse:
        self.calls.append((url, dict(headers)))
        if not self._responses:
            raise AssertionError(f"unexpected request {url}")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client(transport: ScriptedTransport, **kwargs: object) -> PegelClient:
    sleeper = kwargs.pop("sleeper", lambda _seconds: None)
    return PegelClient(
        transport,
        timeout=5,
        max_retries=int(kwargs.pop("max_retries", 2)),  # type: ignore[arg-type]
        backoff_seconds=float(kwargs.pop("backoff_seconds", 1)),  # type: ignore[arg-type]
        user_agent="test-agent",
        sleeper=sleeper,  # type: ignore[arg-type]
    )


class HttpTest(unittest.TestCase):
    def test_gzip_body_is_decoded_and_etag_is_kept(self) -> None:
        raw = gzip.compress(json.dumps(BONN).encode("utf-8"))
        transport = ScriptedTransport(
            [
                HttpResponse(
                    status=200,
                    headers={"etag": '"abc"', "content-encoding": "gzip"},
                    body=raw,
                    url="https://example.test/stations/BONN.json",
                )
            ]
        )
        result = _client(transport).fetch_json("https://example.test/stations/BONN.json")
        self.assertFalse(result.not_modified)
        self.assertEqual(result.payload["shortname"], "BONN")
        self.assertEqual(result.etag, '"abc"')
        sent = transport.calls[0][1]
        self.assertEqual(sent["Accept-Encoding"], "gzip")
        self.assertNotIn("If-None-Match", sent)

    def test_304_does_not_parse_a_body_and_sends_if_none_match(self) -> None:
        transport = ScriptedTransport(
            [
                HttpResponse(
                    status=304,
                    headers={"etag": '"abc"'},
                    body=b"",
                    url="https://example.test/stations/BONN.json",
                )
            ]
        )
        result = _client(transport).fetch_json(
            "https://example.test/stations/BONN.json",
            etag='"abc"',
        )
        self.assertTrue(result.not_modified)
        self.assertIsNone(result.payload)
        self.assertEqual(result.etag, '"abc"')
        self.assertEqual(transport.calls[0][1]["If-None-Match"], '"abc"')

    def test_503_then_200_retries_with_backoff(self) -> None:
        sleeps: list[float] = []
        transport = ScriptedTransport(
            [
                HttpResponse(503, {}, b"", "https://example.test/x"),
                HttpResponse(503, {}, b"", "https://example.test/x"),
                HttpResponse(
                    200,
                    {"etag": '"next"'},
                    json.dumps(BONN).encode("utf-8"),
                    "https://example.test/x",
                ),
            ]
        )
        result = _client(transport, sleeper=sleeps.append, max_retries=2).fetch_json(
            "https://example.test/x"
        )
        self.assertEqual(result.payload["uuid"], BONN["uuid"])
        self.assertEqual(sleeps, [1.0, 2.0])
        self.assertEqual(len(transport.calls), 3)

    def test_404_is_not_retried(self) -> None:
        sleeps: list[float] = []
        transport = ScriptedTransport(
            [HttpResponse(404, {}, b"missing", "https://example.test/nope")]
        )
        with self.assertRaises(HttpError) as caught:
            _client(transport, sleeper=sleeps.append).fetch_json("https://example.test/nope")
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(sleeps, [])
        self.assertEqual(len(transport.calls), 1)

    def test_transport_errors_retry_then_raise(self) -> None:
        sleeps: list[float] = []
        transport = ScriptedTransport(
            [TransportError("timed out"), TransportError("timed out")]
        )
        with self.assertRaises(TransportError):
            _client(transport, sleeper=sleeps.append, max_retries=1).fetch_json(
                "https://example.test/x"
            )
        self.assertEqual(sleeps, [1.0])


if __name__ == "__main__":
    unittest.main()
