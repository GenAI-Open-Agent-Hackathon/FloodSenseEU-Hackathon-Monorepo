"""Poll cycle against scripted PEGELONLINE responses. No network."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from floodsense_live.config import Config, canonical_shortname
from floodsense_live.http import HttpResponse, PegelClient
from floodsense_live.poller import poll_once, station_document_url
from floodsense_live.store import InMemoryGaugeStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BONN = "593647aa-9fea-43ec-a7d6-6476a76ae868"
WHEN = datetime(2026, 10, 23, 16, 20, tzinfo=timezone.utc)
TS_1815 = datetime(2026, 10, 23, 16, 15, tzinfo=timezone.utc)


class ScriptedTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def request(self, url: str, headers: dict[str, str], timeout: float) -> HttpResponse:
        self.calls.append((url, dict(headers)))
        return self._responses.pop(0)


def _config(**env: str) -> Config:
    base = {
        "PEGELONLINE_STATIONS": "BONN",
        "PEGELONLINE_REQUEST_PAUSE_SECONDS": "0",
        "PEGELONLINE_LOOKBACK": "PT45M",
    }
    base.update(env)
    return Config.from_env(base)


def _client(transport: ScriptedTransport) -> PegelClient:
    return PegelClient(
        transport,
        timeout=5,
        max_retries=0,
        backoff_seconds=0,
        user_agent="test-agent",
        sleeper=lambda _seconds: None,
    )


def _json_response(name: str, etag: str, url: str) -> HttpResponse:
    body = (FIXTURES / name).read_bytes()
    return HttpResponse(status=200, headers={"etag": etag}, body=body, url=url)


def _not_modified(etag: str, url: str) -> HttpResponse:
    return HttpResponse(status=304, headers={"etag": etag}, body=b"", url=url)


class PollerTest(unittest.TestCase):
    def test_upsert_then_304_keeps_one_row_per_timestamp(self) -> None:
        station_url = station_document_url(
            "https://pegelonline.wsv.de/webservices/rest-api/v2",
            "BONN",
        )
        transport = ScriptedTransport(
            [
                _json_response("bonn_station.json", '"station"', station_url),
                _json_response("bonn_w_measurements.json", '"meas"', station_url),
                _not_modified('"station"', station_url),
                _not_modified('"meas"', station_url),
            ]
        )
        store = InMemoryGaugeStore()
        client = _client(transport)
        config = _config()
        first = poll_once(
            config,
            client,
            store,
            now=lambda: WHEN,
            pause=lambda _seconds: None,
        )
        self.assertEqual(len(store.stations), 1)
        self.assertEqual(len(store.measurements), 3)
        self.assertEqual(first.not_modified, 0)
        self.assertEqual(first.requests, 2)
        latest = store.measurements[(BONN, "W", TS_1815)]
        self.assertEqual(latest.value, 83.0)
        self.assertEqual(latest.state_mnw_mhw, "low")
        self.assertEqual(latest.unit, "cm")
        self.assertEqual(latest.licence, "DL-DE->Zero-2.0")
        self.assertEqual(latest.source, "PEGELONLINE")
        self.assertEqual(latest.ts_utc.tzinfo, timezone.utc)
        earlier = datetime(2026, 10, 23, 16, 0, tzinfo=timezone.utc)
        self.assertEqual(store.measurements[(BONN, "W", earlier)].value, 84.0)
        self.assertIsNone(store.measurements[(BONN, "W", earlier)].state_mnw_mhw)

        second = poll_once(
            config,
            client,
            store,
            now=lambda: WHEN,
            pause=lambda _seconds: None,
        )
        self.assertEqual(len(store.measurements), 3)
        self.assertEqual(len(store.stations), 1)
        self.assertEqual(second.not_modified, 2)
        self.assertEqual(second.measurements_upserted, 0)
        self.assertEqual(transport.calls[2][1]["If-None-Match"], '"station"')
        self.assertEqual(transport.calls[3][1]["If-None-Match"], '"meas"')
        self.assertNotIn("If-None-Match", transport.calls[0][1])

    def test_all_current_stores_each_station_once(self) -> None:
        payload = json.loads((FIXTURES / "rhein_current_two.json").read_text(encoding="utf-8"))
        body = json.dumps(payload).encode("utf-8")
        url = "https://pegelonline.wsv.de/webservices/rest-api/v2/stations.json"
        transport = ScriptedTransport(
            [
                HttpResponse(200, {"etag": '"list"'}, body, url),
                HttpResponse(304, {"etag": '"list"'}, b"", url),
            ]
        )
        store = InMemoryGaugeStore()
        config = _config(PEGELONLINE_ALL_CURRENT="1", PEGELONLINE_STATIONS="")
        poll_once(config, _client(transport), store, now=lambda: WHEN, pause=lambda _s: None)
        self.assertEqual(len(store.stations), 2)
        self.assertEqual(len(store.measurements), 2)
        names = {row.shortname for row in store.stations.values()}
        self.assertEqual(names, {"BONN", "KÖLN"})
        koeln = next(row for row in store.measurements.values() if row.value == 65.0)
        self.assertEqual(koeln.ts_utc, TS_1815)
        self.assertIn("timeseries=W", transport.calls[0][0])
        self.assertIn("includeCurrentMeasurement=true", transport.calls[0][0])
        poll_once(config, _client(transport), store, now=lambda: WHEN, pause=lambda _s: None)
        self.assertEqual(len(store.measurements), 2)
        self.assertEqual(transport.calls[1][1]["If-None-Match"], '"list"')

    def test_umlaut_alias_is_percent_encoded(self) -> None:
        url = station_document_url("https://example.test", canonical_shortname("koeln"))
        self.assertIn("/stations/K%C3%96LN.json", url)
        self.assertIn("includeTimeseries=true", url)
        self.assertIn("includeCurrentMeasurement=true", url)


if __name__ == "__main__":
    unittest.main()
