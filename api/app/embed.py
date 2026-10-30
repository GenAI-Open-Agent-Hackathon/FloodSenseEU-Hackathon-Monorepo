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
import threading
import time

import httpx

log = logging.getLogger("floodsense.api.embed")

NEBIUS_URL = "https://api.tokenfactory.nebius.com/v1"
NEBIUS_MODEL = "Qwen/Qwen3-Embedding-8B"
BACKOFF_BASE_S, BACKOFF_RETRIES, BACKOFF_MAX_WAIT_S = 2.0, 3, 20.0
# Conservative: a wrong cached answer is worse than a miss. Measured live with
# Qwen3-Embedding-8B: a heavy rewording scored 0.65, an unrelated question 0.43.
DEFAULT_THRESHOLD = 0.85


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
        rpm = float(os.environ.get("NIGHTSHIFT_RPM") or 0)
        self._spacing = 60.0 / rpm if rpm > 0 else 0.0
        self.threshold = float(os.environ.get("EMBED_CACHE_THRESHOLD") or DEFAULT_THRESHOLD)

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

    def embed(self, text: str) -> list[float] | None:
        key = os.environ.get("NEBIUS_API_KEY", "")
        if not self.enabled or not key or not text.strip():
            return None
        base = (os.environ.get("NEBIUS_BASE_URL") or NEBIUS_URL).rstrip("/")
        body = {"model": os.environ.get("NEBIUS_EMBEDDING_MODEL") or NEBIUS_MODEL, "input": [text]}
        client = self._client or httpx.Client()
        waited = 0.0
        for n in range(BACKOFF_RETRIES + 1):
            self._pace()
            try:
                r = client.post(
                    f"{base}/embeddings",
                    json=body,
                    timeout=10.0,
                    headers={"Authorization": f"Bearer {key}"},
                )
                if r.status_code == 429 and n < BACKOFF_RETRIES:
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
