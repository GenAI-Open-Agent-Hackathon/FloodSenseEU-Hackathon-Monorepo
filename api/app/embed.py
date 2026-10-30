"""Question embeddings for the similar-question cache (FF_SEMANTIC_CACHE).

EMBEDDINGS_BACKEND=nim (default: exact-fold matching only, nothing changes) |
nebius. nebius: POST {NEBIUS_BASE_URL}/embeddings, Bearer NEBIUS_API_KEY, model
NEBIUS_EMBEDDING_MODEL (default Qwen/Qwen3-Embedding-8B). The key comes from
the environment only and is never logged. Retry and pacing mirror agents
nightshift.py: 429 backs off 2 s * 2^n (or Retry-After), at most 3 retries and
20 s of extra wait; calls start at least 60/NIGHTSHIFT_RPM s apart. The API
image does not ship the agents package, so this is a small copy.
Any failure returns None: the cache then falls back to exact matching.
"""

from __future__ import annotations

import logging
import math
import os
import random
import re
import threading
import time

import httpx

log = logging.getLogger("floodsense.api.embed")

NEBIUS_URL = "https://api.tokenfactory.nebius.com/v1"
NEBIUS_MODEL = "Qwen/Qwen3-Embedding-8B"
BACKOFF_BASE_S, BACKOFF_RETRIES, BACKOFF_MAX_WAIT_S = 2.0, 3, 20.0
# Live, Qwen3-Embedding-8B: 6 paraphrases scored 0.78 to 0.98 (five at 0.946+), but
# near-misses (negation, number, place, above/below) scored 0.72 to 0.98, so the
# guard_key check, not the threshold, keeps them apart. 0.90 hits 5 of 6.
DEFAULT_THRESHOLD = 0.90
FAST_TIMEOUT_S = 3.0

_NEGATIONS = {"not", "no", "never", "without", "nicht", "kein", "keine", "keinen", "ohne",
              "nie", "nunca", "sin", "ningun", "ninguna", "pas", "sans",
              # antonyms embeddings barely separate (above/below scored 0.98 live)
              "above", "below", "over", "under", "more", "less", "higher", "lower",
              "rising", "falling", "before", "after", "increase", "decrease"}


def _num(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return default


_NUMS = re.compile(r"\d+(?:[.,]\d+)?(?:\s?(?:km|mm|cm|min|ha|hours?|days?|h|m|%))?", re.I)


def guard_key(question: str) -> tuple:
    """What an embedding is weak on: numbers, negations, place names (capitalised
    words that do not start the sentence). Two questions must agree on all three."""
    words = re.findall(r"[\w'.,-]+", question)
    nums = frozenset(m.replace(" ", "").lower() for m in _NUMS.findall(question))
    neg = frozenset(w.lower() for w in words if w.lower().strip(".,") in _NEGATIONS)
    names = frozenset(w.strip(".,'").lower() for w in words[1:] if w[:1].isupper())
    return nums, neg, names


class Embedder:
    def __init__(
        self,
        backend: str | None = None,
        client: httpx.Client | None = None,
        sleep=time.sleep,
    ) -> None:
        self.backend = (backend or os.environ.get("EMBEDDINGS_BACKEND") or "nim").strip().lower()
        self._client = client
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next = 0.0
        rpm = _num("NIGHTSHIFT_RPM", 0.0)
        self._spacing = 60.0 / rpm if rpm > 0 else 0.0
        t = _num("EMBED_CACHE_THRESHOLD", DEFAULT_THRESHOLD)
        self.threshold = t if 0 < t <= 1 else DEFAULT_THRESHOLD

    @property
    def enabled(self) -> bool:
        return self.backend == "nebius"

    def _pace(self) -> None:
        if not self._spacing:
            return
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next)
            self._next = start + self._spacing
        if start > now:
            self._sleep(start - now)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def embed(self, text: str, *, fast: bool = False) -> list[float] | None:
        """fast: one attempt, FAST_TIMEOUT_S, no backoff sleep (the lookup path)."""
        key = os.environ.get("NEBIUS_API_KEY", "")
        if not self.enabled or not key or not text.strip():
            return None
        base = (os.environ.get("NEBIUS_BASE_URL") or NEBIUS_URL).rstrip("/")
        body = {"model": os.environ.get("NEBIUS_EMBEDDING_MODEL") or NEBIUS_MODEL, "input": [text]}
        if self._client is None:
            self._client = httpx.Client()
        client = self._client
        waited = 0.0
        for n in range(1 if fast else BACKOFF_RETRIES + 1):
            if not fast:
                self._pace()
            try:
                r = client.post(
                    f"{base}/embeddings",
                    json=body,
                    timeout=FAST_TIMEOUT_S if fast else 10.0,
                    headers={"Authorization": f"Bearer {key}"},
                )
                if r.status_code == 429 and not fast and n < BACKOFF_RETRIES:
                    try:
                        delay = float(r.headers.get("retry-after"))
                    except (TypeError, ValueError):
                        b = BACKOFF_BASE_S * 2**n
                        delay = b + random.uniform(0, b / 4)
                    if waited + delay > BACKOFF_MAX_WAIT_S:
                        return None
                    waited += delay
                    self._sleep(delay)
                    continue
                r.raise_for_status()
                vec = r.json()["data"][0]["embedding"]
                if not vec or not all(isinstance(x, (int, float)) for x in vec):
                    return None
                return [float(x) for x in vec]
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
                log.warning("embeddings call failed: %s", type(e).__name__)  # never body or key
                return None
        return None


def cosine(a: list[float], b: list[float]) -> float:
    """0.0 when the dimensions differ, so vectors from another model never match."""
    if len(a) != len(b) or not a:
        return 0.0
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0
