"""Similar-question cache with Token Factory embeddings. Mocked transport, no network."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import httpx  # noqa: E402

from app.cache import AnswerCache, CacheSettings  # noqa: E402
from app.embed import Embedder, cosine  # noqa: E402

VECS = {
    "which sites are exposed?": [1.0, 0.0, 0.0],
    "what places are at risk?": [0.97, 0.1, 0.0],  # reworded: cosine ~0.995
    "how deep is the river?": [0.0, 1.0, 0.0],  # unrelated
}


def embedder(calls: list, statuses=None) -> Embedder:
    statuses = list(statuses or [])

    def handler(req: httpx.Request) -> httpx.Response:
        sent = json.loads(req.content)
        calls.append((str(req.url), req.headers["authorization"], sent))
        if statuses:
            st = statuses.pop(0)
            if st != 200:
                return httpx.Response(st, headers={"retry-after": "1"} if st == 429 else {})
        vec = VECS[sent["input"][0].lower()]
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": vec}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Embedder("nebius", client, sleep=lambda s: None)


def run(question: str) -> dict:
    return {
        "run_id": "r1",
        "status": "approved",
        "approval": {"status": "approved"},
        "judge_summary": {"passes": True},
        "request": {"question": question, "event_id": "EMSR773", "customer_id": "demo-insurer"},
    }


@mock.patch.dict(os.environ, {"NEBIUS_API_KEY": "k-test"})
class EmbedCacheTest(unittest.TestCase):
    def cache(self, calls, **kw) -> AnswerCache:
        return AnswerCache(CacheSettings(), embedder=embedder(calls, **kw))

    def test_reworded_repeat_hits_and_unrelated_misses(self) -> None:
        calls: list = []
        c = self.cache(calls)
        self.assertTrue(c.remember(run("Which sites are exposed?"), "f"))
        hit = c.lookup({"question": "What places are at risk?"}, "f")
        self.assertEqual(hit.run_id, "r1")
        self.assertIsNone(c.lookup({"question": "How deep is the river?"}, "f"))
        url, auth, body = calls[0]
        self.assertEqual(url, "https://api.tokenfactory.nebius.com/v1/embeddings")
        self.assertEqual(auth, "Bearer k-test")
        self.assertEqual(body["model"], "Qwen/Qwen3-Embedding-8B")

    def test_other_event_never_matches(self) -> None:
        c = self.cache([])
        c.remember(run("Which sites are exposed?"), "f")
        self.assertIsNone(
            c.lookup({"question": "What places are at risk?", "event_id": "EMSR517"}, "f")
        )

    def test_retries_a_429_then_succeeds(self) -> None:
        calls: list = []
        c = self.cache(calls, statuses=[429])
        self.assertTrue(c.remember(run("Which sites are exposed?"), "f"))
        self.assertEqual(len(calls), 2)
        self.assertIsNotNone(c.lookup({"question": "What places are at risk?"}, "f"))

    def test_failure_falls_back_to_exact_match(self) -> None:
        c = self.cache([], statuses=[500])
        c.remember(run("Which sites are exposed?"), "f")
        self.assertIsNone(c.lookup({"question": "What places are at risk?"}, "f"))
        self.assertIsNotNone(c.lookup({"question": "which sites are exposed"}, "f"))

    def test_other_dimension_never_matches(self) -> None:
        self.assertEqual(cosine([1.0, 0.0], [1.0, 0.0, 0.0]), 0.0)

    def test_default_backend_is_off_and_makes_no_call(self) -> None:
        calls: list = []
        e = embedder(calls)
        e.backend = "nim"
        c = AnswerCache(CacheSettings(), embedder=e)
        c.remember(run("Which sites are exposed?"), "f")
        self.assertIsNone(c.lookup({"question": "What places are at risk?"}, "f"))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
