"""Semantic cache and labelled replay in the API (app/cache.py, app/main.py).

Two kinds of test. The cache rules and the API flow run against a small fake
agents service, so a test decides what the Judge said and when the agents
fail. The replay route runs on the real agents app in-process, as in
test_proxy.py. No network.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "agents"))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import cache as cache_mod  # noqa: E402
from app import main as api  # noqa: E402
from app.cache import AnswerCache, CacheSettings, finished_well, fold, is_follow_up, key_of  # noqa: E402

try:
    from floodsense_agents import __main__ as agents_service  # noqa: E402
except ImportError:  # the agents requirements are not installed here
    agents_service = None

CONFIG = {
    "flags": {"FF_LIVE_DATA": False, "FF_JUDGE": True, "FF_HITL": True},
    "lanes": {"fast": "meterless/fast", "deep": "meterless/deep"},
    "schema": "floodsense_seed",
}


def settings(**kw) -> CacheSettings:
    base = dict(
        semantic_cache=True,
        cached_replay=True,
        ttl_live_s=900,
        ttl_replay_s=86400,
        max_entries=256,
        max_recordings=8,
    )
    base.update(kw)
    return CacheSettings(**base)


def run(run_id="r1", question="Which sites are exposed?", **kw) -> dict:
    out = {
        "run_id": run_id,
        "thread_id": run_id,
        "status": "approved",
        "approval": {"status": "approved"},
        "judge_summary": {"passes": True},
        "request": {"question": question, "event_id": "EMSR773", "customer_id": "demo-insurer"},
    }
    out.update(kw)
    return out


class FoldAndKeyTest(unittest.TestCase):
    def test_case_punctuation_and_spacing_fold_away(self) -> None:
        self.assertEqual(fold("Which  sites are EXPOSED?"), fold("which sites, are exposed"))

    def test_left_out_defaults_key_like_spelled_out_ones(self) -> None:
        bare = {"question": "q"}
        full = {"question": "q", "event_id": "EMSR773", "customer_id": "demo-insurer", "lang": "en"}
        self.assertEqual(key_of(bare, "f"), key_of(full, "f"))

    def test_event_replay_clock_and_flags_are_part_of_the_key(self) -> None:
        q = {"question": "q"}
        self.assertNotEqual(key_of(q, "f"), key_of({**q, "event_id": "EMSR517"}, "f"))
        self.assertNotEqual(key_of(q, "f"), key_of({**q, "replay_ts": "2024-10-29T16:00:00Z"}, "f"))
        self.assertNotEqual(key_of(q, "f"), key_of(q, "g"))


class QualifyTest(unittest.TestCase):
    def test_only_a_person_approved_and_judge_passed_run_qualifies(self) -> None:
        self.assertTrue(finished_well(run()))
        self.assertTrue(finished_well(run(approval={"status": "edited"})))
        self.assertFalse(finished_well(run(approval={"status": "auto"})))
        self.assertFalse(finished_well(run(status="rejected", approval={"status": "rejected"})))
        self.assertFalse(finished_well(run(judge_summary={"passes": False})))
        self.assertFalse(finished_well(run(judge_summary=None)))

    def test_a_follow_up_is_recognised(self) -> None:
        self.assertFalse(is_follow_up(run()))
        self.assertTrue(is_follow_up(run(thread_id="r0")))
        self.assertTrue(is_follow_up(run(request={"question": "q", "thread_id": "r0"})))


class AnswerCacheTest(unittest.TestCase):
    def test_a_finished_run_is_found_again(self) -> None:
        c = AnswerCache(settings())
        self.assertTrue(c.remember(run(), "f"))
        hit = c.lookup({"question": "which sites are exposed"}, "f")
        self.assertEqual(hit.run_id, "r1")

    def test_follow_ups_are_never_cached_or_served(self) -> None:
        c = AnswerCache(settings())
        self.assertFalse(c.remember(run(thread_id="r0"), "f"))
        c.remember(run(), "f")
        self.assertIsNone(
            c.lookup({"question": "Which sites are exposed?", "thread_id": "r1"}, "f")
        )

    def test_live_data_expires_sooner_than_a_historical_replay(self) -> None:
        c = AnswerCache(settings(ttl_live_s=10, ttl_replay_s=1000))
        live = "FF_LIVE_DATA=True;schema=floodsense"
        self.assertEqual(c.ttl_for({"question": "q"}, live), 10)
        self.assertEqual(
            c.ttl_for({"question": "q", "replay_ts": "2024-10-29T16:00:00Z"}, live), 1000
        )
        self.assertEqual(c.ttl_for({"question": "q"}, "FF_LIVE_DATA=False"), 1000)

    def test_an_expired_entry_is_a_miss(self) -> None:
        c = AnswerCache(settings(ttl_replay_s=60))
        with mock.patch.object(cache_mod.time, "time", return_value=1000.0):
            c.remember(run(), "f")
        with mock.patch.object(cache_mod.time, "time", return_value=1059.0):
            self.assertIsNotNone(c.lookup({"question": "Which sites are exposed?"}, "f"))
        with mock.patch.object(cache_mod.time, "time", return_value=1061.0):
            self.assertIsNone(c.lookup({"question": "Which sites are exposed?"}, "f"))

    def test_the_oldest_entry_goes_first_when_full(self) -> None:
        c = AnswerCache(settings(max_entries=2))
        for i in range(3):
            c.remember(run(f"r{i}", question=f"q{i}"), "f")
        self.assertIsNone(c.lookup({"question": "q0"}, "f"))
        self.assertEqual(c.lookup({"question": "q2"}, "f").run_id, "r2")

    def test_drop_forgets_a_run(self) -> None:
        c = AnswerCache(settings())
        c.remember(run(), "f")
        c.drop("r1")
        self.assertIsNone(c.lookup({"question": "Which sites are exposed?"}, "f"))

    def test_recordings_keep_the_newest_per_event_and_customer(self) -> None:
        c = AnswerCache(settings(max_recordings=1))
        c.record({"run_id": "a", "event_id": "EMSR773", "customer_id": "demo-insurer"})
        c.record({"run_id": "b", "event_id": "EMSR517", "customer_id": "demo-insurer"})
        self.assertIsNone(c.recording("EMSR773", "demo-insurer"))
        self.assertEqual(c.recording("EMSR517", "demo-insurer")["run_id"], "b")


class FakeAgents:
    """The agents' run routes in miniature. A test sets judge_passes, config and failures."""

    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}
        self.config = dict(CONFIG)
        self.judge_passes = True
        self.down = False
        self.post_status = 201
        self.fail_runs = False
        self.started = 0

    def __call__(self, method, path, body=None, params=None):
        if self.down:
            raise httpx.ConnectError("connection refused")
        json = body
        if path == "/config":
            return httpx.Response(200, json=self.config)
        if method == "POST" and path == "/runs":
            if self.post_status >= 500:
                return httpx.Response(self.post_status, json={"detail": "boom"})
            self.started += 1
            rid = f"run{self.started}"
            body = {
                "run_id": rid,
                "thread_id": (json or {}).get("thread_id") or rid,
                "event_id": (json or {}).get("event_id") or "EMSR773",
                "customer_id": (json or {}).get("customer_id") or "demo-insurer",
                "request": dict(json or {}),
                "status": "failed" if self.fail_runs else "awaiting_approval",
                "error": "Nightshift unreachable" if self.fail_runs else None,
                "approval": {"status": "awaiting"},
                "judge_summary": {"passes": self.judge_passes},
                "created_at": f"2026-10-25T14:3{self.started}:00Z",
                "served_from": "live",
                "cached_at": None,
            }
            self.runs[rid] = body
            return httpx.Response(201, json=body)
        if method == "POST" and path.endswith("/approval"):
            rid = path.split("/")[2]
            action = (json or {}).get("action")
            r = self.runs[rid]
            r["status"] = "rejected" if action == "reject" else "approved"
            r["approval"] = {
                "status": {"approve": "approved", "edit": "edited"}.get(action, "rejected")
            }
            return httpx.Response(200, json=r)
        if path == "/runs/past":
            rows = [
                {
                    "run_id": r["run_id"],
                    "thread_id": r["thread_id"],
                    "event_id": r["event_id"],
                    "customer_id": r["customer_id"],
                    "status": r["status"],
                    "approval": r["approval"]["status"],
                }
                for r in reversed(list(self.runs.values()))
            ]
            return httpx.Response(200, json={"runs": rows})
        if path.startswith("/runs/") and path.endswith("/replay"):
            rid = path.split("/")[2]
            r = self.runs.get(rid)
            if r is None:
                return httpx.Response(404, json={"detail": "not found"})
            return httpx.Response(
                200, json={**r, "served_from": "replay", "cached_at": r["created_at"]}
            )
        if path.startswith("/runs/"):
            rid = path.split("/")[2]
            r = self.runs.get(rid)
            if r is None:
                return httpx.Response(404, json={"detail": "not found"})
            return httpx.Response(
                200, json={**r, "served_from": "cache", "cached_at": r["created_at"]}
            )
        return httpx.Response(404, json={"detail": f"no route {method} {path}"})


class ApiFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agents = FakeAgents()
        self._patches = [
            mock.patch.object(api, "_agents_request", side_effect=self.agents),
            mock.patch.object(api, "cache", AnswerCache(settings())),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        self.c = TestClient(api.app)

    def finished(self, question="Which sites are exposed?", action="approve", **extra) -> dict:
        r = self.c.post("/runs", json={"question": question, **extra})
        self.assertEqual(r.status_code, 201)
        rid = r.json()["run_id"]
        self.c.post(f"/runs/{rid}/approval", json={"action": action, "reviewer": "ayush"})
        return r.json()

    def test_a_repeat_of_a_finished_question_is_served_from_the_cache(self) -> None:
        first = self.finished()
        r = self.c.post("/runs", json={"question": "which sites are EXPOSED"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["served_from"], "cache")
        self.assertEqual(body["cache"]["original_run_id"], first["run_id"])
        self.assertEqual(body["cached_at"], first["created_at"])
        self.assertEqual(self.agents.started, 1)

    def test_fresh_skips_the_cache(self) -> None:
        self.finished()
        r = self.c.post("/runs", json={"question": "Which sites are exposed?", "fresh": True})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["served_from"], "live")
        self.assertNotIn("fresh", r.json()["request"])
        self.assertEqual(self.agents.started, 2)

    def test_a_run_the_judge_did_not_pass_is_not_cached(self) -> None:
        self.agents.judge_passes = False
        self.finished()
        self.assertEqual(
            self.c.post("/runs", json={"question": "Which sites are exposed?"}).status_code, 201
        )

    def test_a_rejected_run_is_not_cached(self) -> None:
        self.finished(action="reject")
        self.assertEqual(
            self.c.post("/runs", json={"question": "Which sites are exposed?"}).status_code, 201
        )

    def test_a_follow_up_is_never_served_from_the_cache(self) -> None:
        first = self.finished()
        r = self.c.post(
            "/runs", json={"question": "Which sites are exposed?", "thread_id": first["run_id"]}
        )
        self.assertEqual(r.status_code, 201)

    def test_a_change_of_agents_flags_is_a_miss(self) -> None:
        self.finished()
        self.agents.config = {**CONFIG, "flags": {**CONFIG["flags"], "FF_LIVE_DATA": True}}
        api.cache.forget_flags()
        self.assertEqual(
            self.c.post("/runs", json={"question": "Which sites are exposed?"}).status_code, 201
        )

    def test_the_cache_is_off_without_its_flag(self) -> None:
        api.cache.settings.semantic_cache = False
        self.finished()
        self.assertEqual(
            self.c.post("/runs", json={"question": "Which sites are exposed?"}).status_code, 201
        )

    def test_agents_down_serves_the_last_recording_labelled_replay(self) -> None:
        first = self.finished()
        self.agents.down = True
        r = self.c.post("/runs", json={"question": "Something new?"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["served_from"], "replay")
        self.assertEqual(body["replay"]["original_run_id"], first["run_id"])
        self.assertIn("could not be reached", body["replay"]["reason"])

    def test_a_5xx_from_the_agents_serves_a_recorded_run(self) -> None:
        first = self.finished()
        self.agents.post_status = 500
        body = self.c.post("/runs", json={"question": "Something new?"}).json()
        self.assertEqual(body["served_from"], "replay")
        self.assertEqual(body["replay"]["original_run_id"], first["run_id"])
        self.assertIn("HTTP 500", body["replay"]["reason"])

    def test_a_failed_live_run_serves_a_recorded_run(self) -> None:
        first = self.finished()
        self.agents.fail_runs = True
        body = self.c.post("/runs", json={"question": "Something new?"}).json()
        self.assertEqual(body["served_from"], "replay")
        self.assertEqual(body["replay"]["original_run_id"], first["run_id"])
        self.assertIn("Nightshift unreachable", body["replay"]["reason"])

    def test_only_a_person_approved_run_is_replayed(self) -> None:
        self.finished(action="reject")
        self.agents.post_status = 500
        self.assertEqual(self.c.post("/runs", json={"question": "Something new?"}).status_code, 500)

    def test_no_recording_keeps_the_503(self) -> None:
        self.agents.down = True
        self.assertEqual(self.c.post("/runs", json={"question": "q"}).status_code, 503)

    def test_replay_is_off_without_its_flag(self) -> None:
        api.cache.settings.cached_replay = False
        self.finished()
        self.agents.down = True
        self.assertEqual(self.c.post("/runs", json={"question": "q"}).status_code, 503)

    def test_config_reports_the_cache(self) -> None:
        stats = self.c.get("/config").json()["api_cache"]
        self.assertTrue(stats["FF_SEMANTIC_CACHE"])
        self.assertTrue(stats["FF_CACHED_REPLAY"])


@unittest.skipIf(agents_service is None, "agents package not importable")
class AgentsReplayRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver
        from floodsense_agents.graph import build_graph
        from floodsense_agents.nightshift import FakeNightshift
        from floodsense_agents.runtime import Runtime
        from floodsense_agents.state import Deps, NoMemory
        from floodsense_agents.zetaris import FakeZetaris

        deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
        agents_service.set_runtime(Runtime(graph=build_graph(deps, MemorySaver()), deps=deps))
        self.c = TestClient(agents_service.app)

    def test_a_recorded_run_is_labelled_replay_with_its_start_time(self) -> None:
        rid = self.c.post("/runs", json={"question": "Which sites are exposed?"}).json()["run_id"]
        self.c.post(f"/runs/{rid}/approval", json={"action": "approve", "reviewer": "ayush"})
        started = next(r for r in self.c.get("/runs/past").json()["runs"] if r["run_id"] == rid)
        body = self._replay_without_listing_checkpoints(rid)
        self.assertEqual(body["served_from"], "replay")
        self.assertEqual(body["cached_at"], started["created_at"])
        self.assertFalse(body["label"]["live"])
        self.assertTrue(body["label"]["text"].startswith("Replay of a recorded run from"))
        self.assertIn(f"original run {rid}", body["label"]["text"])

    def test_replay_after_a_restart_still_does_not_list_every_checkpoint(self) -> None:
        rid = self.c.post("/runs", json={"question": "Which sites are exposed?"}).json()["run_id"]
        started = next(r for r in self.c.get("/runs/past").json()["runs"] if r["run_id"] == rid)
        agents_service.runtime().index.clear()
        body = self._replay_without_listing_checkpoints(rid)
        self.assertEqual(body["served_from"], "replay")
        self.assertEqual(body["cached_at"], started["created_at"])
        self.assertEqual(len(agents_service.runtime().index), 1)

    def _replay_without_listing_checkpoints(self, rid: str) -> dict:
        rt = agents_service.runtime()
        calls = {"rebuild": 0}
        real = rt._rebuild_index

        def rebuild():
            calls["rebuild"] += 1
            return real()

        rt._rebuild_index = rebuild
        try:
            response = self.c.get(f"/runs/{rid}/replay")
        finally:
            rt._rebuild_index = real
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(calls["rebuild"], 0)
        return response.json()

    def test_an_unknown_run_is_a_404(self) -> None:
        self.assertEqual(self.c.get("/runs/nope/replay").status_code, 404)


if __name__ == "__main__":
    unittest.main()
