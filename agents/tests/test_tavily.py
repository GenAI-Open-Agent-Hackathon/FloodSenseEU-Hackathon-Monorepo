"""Tavily web context. Offline: httpx.MockTransport only."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

import httpx  # noqa: E402

from floodsense_agents import tavily  # noqa: E402
from floodsense_agents.models import Evidence  # noqa: E402
from floodsense_agents.nodes.investigator import _attach_web  # noqa: E402
from floodsense_agents.nodes.judge import score_claim  # noqa: E402
from floodsense_agents.settings import settings  # noqa: E402

OK = {
    "results": [
        {
            "title": "Flood alert for Koeln",
            "url": "https://example.org/a",
            "content": 'City says "stay away" from the 5 m bank. ' * 8,
            "score": 0.9,
        },
        {"title": "bad", "url": "ftp://x", "content": "ignored"},
    ]
}


def mock(handler):
    return httpx.MockTransport(handler)


class TavilyTest(unittest.TestCase):
    def setUp(self):
        tavily._cache.clear()
        tavily._last_call = 0.0
        self._key = settings.tavily_api_key
        settings.tavily_api_key = "tvly-test"

    def tearDown(self):
        settings.tavily_api_key = self._key

    def test_success_request_shape(self):
        seen = {}

        def h(req):
            seen["auth"] = req.headers["authorization"]
            seen["url"] = str(req.url)
            return httpx.Response(200, json=OK)

        r = tavily.search("Koeln", transport=mock(h))
        self.assertEqual(r.status, "ok")
        self.assertEqual(len(r.items), 1)
        self.assertEqual(seen["auth"], "Bearer tvly-test")
        self.assertEqual(seen["url"], tavily.URL)

    def test_empty(self):
        r = tavily.search("Koeln", transport=mock(lambda q: httpx.Response(200, json={"results": []})))
        self.assertEqual(r.status, "empty")

    def test_errors_degrade(self):
        for code in (429, 432, 500):
            tavily._cache.clear()
            tavily._last_call = 0.0
            r = tavily.search("Koeln", transport=mock(lambda q, c=code: httpx.Response(c)))
            self.assertEqual(r.status, "unavailable")

    def test_timeout_degrades(self):
        def h(req):
            raise httpx.ReadTimeout("slow")

        self.assertEqual(tavily.search("Koeln", transport=mock(h)).status, "unavailable")

    def test_no_key(self):
        settings.tavily_api_key = None
        self.assertEqual(tavily.search("Koeln").reason, "TAVILY_API_KEY not set")

    def test_cache_and_rate_guard(self):
        n = []

        def h(req):
            n.append(1)
            return httpx.Response(200, json=OK)

        tavily.search("Koeln", transport=mock(h))
        tavily.search("Koeln", transport=mock(h))
        self.assertEqual(len(n), 1)
        self.assertEqual(tavily.search("Bonn", transport=mock(h)).reason, "rate guard")

    def test_flag_default_off(self):
        self.assertFalse(settings.ff_tavily)

    def test_claims_are_labelled_cited_and_judged(self):
        res = tavily.search("Koeln", transport=mock(lambda q: httpx.Response(200, json=OK)))
        from floodsense_agents import tavily as t

        orig = t.search
        t.search = lambda place: res
        try:
            claims, ev, _ = _attach_web([], "Koeln", "")
        finally:
            t.search = orig
        self.assertEqual(len(claims), 1)
        c = claims[0]
        self.assertTrue(c.text.startswith(tavily.LABEL))
        self.assertEqual(c.numbers, [])
        self.assertEqual(c.citations[0].source_url, "https://example.org/a")
        evidence = {e.query_id: e for e in ev}
        self.assertIsInstance(ev[0], Evidence)
        s = score_claim(c, evidence, None)
        self.assertTrue(s.citation_faithful)
        self.assertTrue(s.numbers_match)


if __name__ == "__main__":
    unittest.main()
