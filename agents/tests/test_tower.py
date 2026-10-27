"""Control tower: status diffing, the event schema, the caps and switches, persistence, the forecast hook.

No network and no model: a stub Zetaris answers the views, and the run lifecycle uses the fakes.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts" / "python"))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from fastapi.testclient import TestClient  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from floodsense_contracts.models import WatchEvent, WatchStatus  # noqa: E402
from floodsense_agents import __main__ as service  # noqa: E402
from floodsense_agents import router, tower  # noqa: E402
from floodsense_agents.graph import build_graph  # noqa: E402
from floodsense_agents.models import Evidence, RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.runtime import Runtime  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris, now_utc  # noqa: E402


def iso(delta_h: float = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=delta_h)).strftime("%Y-%m-%dT%H:%M:%SZ")


def gauge(station="KÖLN", water="RHEIN", level=812, mhw=780, band="above", stale=False):
    return {
        "station": station, "water": water, "ts_utc": iso(-1), "level_cm": level, "mhw_cm": mhw,
        "mw_cm": 300, "band": band, "is_stale": stale, "trend_cm_h": 2,
    }  # fmt: skip


def eu(pid="EU03", name="Orleans", river="Loire", cc="FR", band="above", fmax=840, med=350):
    return {
        "point_id": pid, "name": name, "country": cc, "river": river, "lat": 47.875, "lon": 1.875,
        "discharge_m3s": 400, "forecast_max_m3s": fmax, "past30_median_m3s": med, "band": band,
    }  # fmt: skip


def hazard(pid="VAL01", now_q=4.0, fmax=180.0):
    rows = []
    for h in range(-5, 1):
        rows.append({"point_id": pid, "ts_utc": iso(h), "discharge_m3s": now_q, "horizon": "past"})
    for h in range(1, 49):
        q = fmax if h == 20 else 4.0
        rows.append({"point_id": pid, "ts_utc": iso(h), "discharge_m3s": q, "horizon": "forecast"})
    return rows


def weather(pid, r48=12.0, hour=3.0):
    return {
        "point_id": pid, "name": pid, "river": "", "rain_48h_mm": r48, "rain_72h_mm": r48 + 1,
        "max_hour_48h_mm": hour, "from_utc": iso(0), "to_utc": iso(72), "hours": 72,
    }  # fmt: skip


class Stub:
    """Answers each contract view with canned rows and records every query."""

    def __init__(self, gauges=(), eus=(), hazards=(), weathers=(), exposure=None, fail=()):
        self.rows = {
            "gauge_levels": list(gauges), "eu_watch": list(eus), "hazard_now": list(hazards),
            "weather_forecast": list(weathers),
            "exposure_join": [exposure] if exposure else [{"sites": 0, "policies": 0, "insured_eur": None}],
        }  # fmt: skip
        self.fail = set(fail)
        self.queries: list[tuple[str, str]] = []

    def run_sql(self, sql, params=None, sample=20):
        view = next(v for v in self.rows if v in sql)
        self.queries.append((view, sql))
        err = "boom" if view in self.fail else None
        rows = [] if err else self.rows[view]
        return Evidence(
            query_id=f"q-{len(self.queries)}", view=view, sql=sql, rows_sample=rows[:sample],
            row_count=len(rows), executed_at_utc=now_utc(), error=err,
        )  # fmt: skip


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class FakeRuntime:
    """Records start_async calls; snapshot is whatever a test sets."""

    def __init__(self):
        self.started: list[RunRequest] = []
        self.snaps: dict[str, dict] = {}

    def start_async(self, req):
        self.started.append(req)
        return {"run_id": f"run{len(self.started)}", "thread_id": "t", "status": "running"}

    def snapshot(self, run_id):
        return self.snaps[run_id]


def make(stub, tmp, **kw):
    kw.setdefault("clock", Clock())
    kw.setdefault("loop_enabled", False)
    return tower.ControlTower(lambda: stub, kw.pop("runtime", None), data_dir=tmp, **kw)


def full_stub(**kw):
    base = dict(
        gauges=[gauge(), gauge("BONN", level=300, mhw=700, band="below")],
        eus=[eu(), eu("EU04", "Piacenza", "Po", "IT", band="near", fmax=500, med=300), eu("EU01", "Paris", "Seine", "FR", band="below", fmax=100, med=120)],
        hazards=hazard("VAL01"),
        weathers=[weather("PEG07"), weather("EU03", 60.0, 31.0), weather("EU04"), weather("VAL01", 5.0, 1.0)],
        exposure={"sites": 4, "policies": 5, "insured_eur": 12_000_000.0},
    )  # fmt: skip
    base.update(kw)
    return Stub(**base)


class StatusTest(unittest.TestCase):
    def test_plain_words_and_tones_match_the_ui(self):
        words = {
            ("gauge", "over"): ("Above mean high water", "elevated"),
            ("gauge", "near"): ("Close to mean high water", "watch"),
            ("model", "over"): ("Elevated (model)", "elevated"),
            ("model", "near"): ("Watch (model)", "watch"),
            ("valencia", "over"): ("Above 80 m³/s demo line", "elevated"),
            ("valencia", "near"): ("Above 20 m³/s demo line", "neutral"),
            ("gauge", "ok"): ("Normal", "normal"),
            ("model", "unknown"): ("No reading", "unknown"),
        }
        for (kind, st), (word, tone) in words.items():
            v = tower.status_view(kind, st)
            self.assertEqual((v["word"], v["tone"]), (word, tone))
        for kind in ("gauge", "model", "valencia"):
            for st in ("ok", "near", "over", "unknown"):
                v = tower.status_view(kind, st)
                self.assertNotIn("warning", v["word"].lower())
                self.assertNotIn("red", v["tone"])

    def test_gauge_status_band_stale_and_computed(self):
        self.assertEqual(tower.gauge_status(gauge(band="above")), "over")
        self.assertEqual(tower.gauge_status(gauge(band="near")), "near")
        self.assertEqual(tower.gauge_status(gauge(band="below")), "ok")
        self.assertEqual(tower.gauge_status(gauge(stale=True)), "unknown")
        # no band column: level vs MHW, "near" = within 25 % of the MW..MHW span below MHW
        base = {"mhw_cm": 800, "mw_cm": 400}
        self.assertEqual(tower.gauge_status({**base, "level_cm": 800}), "over")
        self.assertEqual(tower.gauge_status({**base, "level_cm": 710}), "near")
        self.assertEqual(tower.gauge_status({**base, "level_cm": 690}), "ok")
        self.assertEqual(tower.gauge_status({"level_cm": 100}), "unknown")

    def test_valencia_takes_the_higher_of_now_and_the_48h_forecast(self):
        ev = Stub(
            hazards=hazard("VAL01", 4.0, 180.0) + hazard("VAL02", 25.0, 4.0) + hazard("VAL03")[:6]
        ).run_sql("hazard_now", None, 6000)
        by = {s["ref"]: s for s in tower.valencia_sources(ev)}
        self.assertEqual(by["VAL01"]["status"], "over")  # forecast 180 >= 80
        self.assertEqual(by["VAL02"]["status"], "near")  # now 25 >= 20
        self.assertEqual(by["VAL03"]["status"], "ok")


class DiffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def kinds(self, t, since=None):
        return [(e["kind"], e["place"]) for e in t.store.since(since, 500)]

    def test_first_cycle_flags_every_elevated_source_then_nothing_new(self):
        t = make(full_stub(), self.tmp.name)
        out = t.cycle()
        self.assertTrue(out["ran"])
        self.assertEqual((out["sources"], out["elevated"], out["new"]), (3 + 2 + 1, 4, 4))
        detected = {p for k, p in self.kinds(t) if k == "detected"}
        self.assertEqual(detected, {"Köln", "Orleans", "Piacenza", "Paiporta"})
        last = t.store.latest_id()
        out2 = t.cycle()
        self.assertEqual(out2["new"], 0)
        self.assertEqual(t.store.since(last, 50), [])  # an unchanged world adds nothing

    def test_escalation_is_flagged_and_says_where_it_came_from(self):
        stub = full_stub(eus=[eu("EU04", "Piacenza", "Po", "IT", band="near", fmax=500, med=300)])
        t = make(stub, self.tmp.name)
        t.cycle()
        mark = t.store.latest_id()
        stub.rows["eu_watch"] = [
            eu("EU04", "Piacenza", "Po", "IT", band="above", fmax=700, med=300)
        ]
        out = t.cycle()
        self.assertEqual(out["new"], 1)
        ev = [e for e in t.store.since(mark, 50) if e["kind"] == "detected"]
        self.assertEqual(len(ev), 1)
        self.assertIn("Elevated (model)", ev[0]["text"])
        self.assertIn("up from watch (model)", ev[0]["text"])
        # a drop from above to near is not a new alarm
        mark = t.store.latest_id()
        stub.rows["eu_watch"] = [eu("EU04", "Piacenza", "Po", "IT", band="near", fmax=500, med=300)]
        self.assertEqual(t.cycle()["new"], 0)
        self.assertEqual([e for e in t.store.since(mark, 50) if e["kind"] == "detected"], [])

    def test_return_to_normal_is_an_info_event(self):
        stub = full_stub(eus=[eu("EU04", "Piacenza", "Po", "IT", band="near", fmax=500, med=300)])
        t = make(stub, self.tmp.name)
        t.cycle()
        mark = t.store.latest_id()
        stub.rows["eu_watch"] = [
            eu("EU04", "Piacenza", "Po", "IT", band="below", fmax=100, med=300)
        ]
        t.cycle()
        info = [e for e in t.store.since(mark, 50) if e["kind"] == "info"]
        self.assertEqual(len(info), 1)
        self.assertIn("back to normal", info[0]["text"])

    def test_a_view_that_cannot_be_read_keeps_its_last_status(self):
        stub = full_stub()
        t = make(stub, self.tmp.name)
        t.cycle()
        mark = t.store.latest_id()
        stub.fail = {"eu_watch"}
        out = t.cycle()
        self.assertIn("eu_watch", out["errors"])
        new = t.store.since(mark, 50)
        self.assertEqual([e["kind"] for e in new], ["info"])  # one note, no false "recovered"
        self.assertIn("Could not read eu_watch", new[0]["text"])
        stub.fail = set()
        mark = t.store.latest_id()
        self.assertEqual(t.cycle()["new"], 0)  # the Loire is not "new" again after the outage
        self.assertEqual([e["text"] for e in t.store.since(mark, 50)], ["eu_watch answers again."])

    def test_a_stale_gauge_is_never_an_event(self):
        t = make(full_stub(gauges=[gauge(stale=True)], eus=[], hazards=[]), self.tmp.name)
        self.assertEqual(t.cycle()["new"], 0)


class EventTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_every_event_matches_the_contract_and_uses_fixed_templates(self):
        t = make(full_stub(), self.tmp.name)
        t.cycle()
        events = t.store.all()
        self.assertGreaterEqual(
            {e["kind"] for e in events}, {"detected", "checked", "exposure", "info"}
        )
        ids = [e["id"] for e in events]
        self.assertEqual(ids, sorted(ids))
        for e in events:
            WatchEvent.model_validate(e)
            self.assertIn(e["agent"], tower.AGENTS)
            self.assertEqual(e["agent"], tower.KIND_AGENT[e["kind"]])
            self.assertNotIn("Warning", e["status"])
        orleans = next(e for e in events if e["kind"] == "detected" and e["place"] == "Orleans")
        self.assertEqual(orleans["place_id"], "model:EU03")
        self.assertEqual(
            orleans["source"], {"view": "eu_watch", "query_id": orleans["source"]["query_id"]}
        )
        self.assertEqual(
            orleans["text"],
            "Loire at Orleans: Elevated (model). The 7-day model maximum is 840 m³/s, 2.4 times the "
            "past-30-day median of 350 m³/s. Model, not an official warning.",
        )

    def test_numbers_in_the_text_come_from_the_rows(self):
        t = make(full_stub(), self.tmp.name)
        t.cycle()
        cologne = next(e for e in t.store.all() if e["kind"] == "detected" and e["place"] == "Köln")
        self.assertIn("Level 812 cm against a long-term mean high water of 780 cm", cologne["text"])
        self.assertIn("Not a warning level", cologne["text"])
        self.assertTrue(cologne["text"].startswith("Rhine at Köln: above mean high water"))

    def test_forecast_hook_records_rain_forecast_max_and_screening(self):
        stub = full_stub()
        t = make(stub, self.tmp.name)
        t.cycle()
        checked = {e["place"]: e for e in t.store.all() if e["kind"] == "checked"}
        self.assertEqual(set(checked), {"Köln", "Orleans", "Piacenza", "Paiporta"})
        o = checked["Orleans"]
        self.assertEqual(o["agent"], "Forecast")
        self.assertEqual(o["data"]["rain_48h_mm"], 60.0)
        self.assertEqual(o["data"]["forecast_max_m3s"], 840)
        self.assertEqual(o["data"]["screening"], "Warning")  # the lane's own cut: 50 mm in 48 h
        self.assertIn("rain forecast 60 mm over the next 48 h (wettest hour 31 mm)", o["text"])
        self.assertIn("FloodSense screening: elevated", o["text"])
        self.assertEqual(checked["Piacenza"]["data"]["screening"], "Watch")  # band near
        self.assertEqual(o["source"]["view"], "weather_forecast")
        # one weather query serves every flagged place
        self.assertEqual(sum(1 for v, _ in stub.queries if v == "weather_forecast"), 1)

    def test_forecast_gap_is_stated_not_invented(self):
        stub = full_stub(
            weathers=[],
            eus=[{**eu(band="near", fmax=None, med=None), "discharge_m3s": None}],
            gauges=[],
            hazards=[],
        )
        t = make(stub, self.tmp.name)
        t.cycle()
        chk = next(e for e in t.store.all() if e["kind"] == "checked")
        self.assertIn("no forecast rows are held for this place right now", chk["text"])

    def test_exposure_only_for_valencia_and_the_demo_books_area(self):
        stub = full_stub()
        t = make(stub, self.tmp.name)
        t.cycle()
        ex = [e for e in t.store.all() if e["kind"] == "exposure"]
        self.assertEqual([e["place"] for e in ex], ["Paiporta"])
        self.assertEqual(ex[0]["data"]["sites"], 4)
        self.assertIn(
            "4 insured sites of the demo book within about 25 km, 12,000,000 EUR", ex[0]["text"]
        )
        self.assertEqual(ex[0]["agent"], "Exposure")
        queries = [s for v, s in stub.queries if v == "exposure_join"]
        self.assertEqual(len(queries), 1)
        self.assertIn("BETWEEN", queries[0])
        self.assertTrue(tower.near_demo_book({"kind": "valencia", "row": {}, "ref": "VAL01"}))
        self.assertFalse(
            tower.near_demo_book({"kind": "model", "ref": "EU01", "row": {"lat": 48.9, "lon": 2.3}})
        )
        self.assertTrue(
            tower.near_demo_book({"kind": "model", "ref": "X", "row": {"lat": 39.45, "lon": -0.4}})
        )

    def test_story_is_per_source_and_nearby_points_share_one_exposure_read(self):
        stub = full_stub(
            hazards=hazard("VAL01") + hazard("VAL02", 25.0, 4.0),
            eus=[],
            gauges=[],
            weathers=[weather("VAL01"), weather("VAL02")],
        )
        t = make(stub, self.tmp.name)
        t.cycle()
        story = [(e["kind"], e["place"]) for e in t.store.all() if e["kind"] != "info"]
        self.assertEqual(
            story,
            [
                ("detected", "Paiporta"),  # worst first: above the 80 m³/s demo line
                ("checked", "Paiporta"),
                ("exposure", "Paiporta"),
                ("detected", "Catarroja"),
                ("checked", "Catarroja"),
            ],
        )
        ex = next(e for e in t.store.all() if e["kind"] == "exposure")
        self.assertEqual(ex["data"]["also_covers"], ["Catarroja"])
        self.assertIn("(also covering Catarroja)", ex["text"])
        self.assertEqual(sum(1 for v, _ in stub.queries if v == "exposure_join"), 1)

    def test_exposure_zero_sites_says_so(self):
        stub = full_stub(exposure={"sites": 0, "policies": 0, "insured_eur": None})
        t = make(stub, self.tmp.name)
        t.cycle()
        ex = next(e for e in t.store.all() if e["kind"] == "exposure")
        self.assertIn("no insured sites of the demo book within about 25 km", ex["text"])

    def test_with_the_fake_zetaris_a_cycle_runs_without_a_model(self):
        t = tower.ControlTower(
            lambda: FakeZetaris(), None, data_dir=self.tmp.name, loop_enabled=False
        )
        out = t.cycle()
        self.assertTrue(out["ran"])
        self.assertEqual(out["errors"], {})


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def ev(self, i):
        return {"kind": "info", "agent": "Watch", "place": "", "river": "", "country": "", "status": "",
                "tone": "unknown", "text": f"e{i}", "source": {"view": "watch", "query_id": None}, "data": {}}  # fmt: skip

    def test_ring_is_bounded_at_500_and_since_pages(self):
        s = tower.EventStore(self.tmp.name)
        for i in range(520):
            s.append(self.ev(i))
        self.assertEqual(len(s), 500)
        self.assertEqual(s.all()[0]["text"], "e20")
        self.assertEqual(len(s.since(None, 1000)), 500)
        first = s.since("w00000100", 5)
        self.assertEqual([e["id"] for e in first], [f"w{n:08d}" for n in range(101, 106)])
        self.assertEqual(s.since(s.latest_id()), [])
        self.assertEqual([e["text"] for e in s.since(None, 3)], ["e517", "e518", "e519"])

    def test_history_survives_a_restart_and_ids_keep_counting(self):
        s = tower.EventStore(self.tmp.name)
        for i in range(3):
            s.append(self.ev(i))
        again = tower.EventStore(self.tmp.name)
        self.assertEqual([e["text"] for e in again.all()], ["e0", "e1", "e2"])
        new = again.append(self.ev(3))
        self.assertEqual(new["id"], "w00000004")
        lines = (
            (Path(self.tmp.name) / "watch_events.jsonl").read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(len(lines), 4)
        self.assertEqual(json.loads(lines[-1])["text"], "e3")

    def test_a_restart_remembers_statuses_so_the_loire_is_not_new_again(self):
        stub = full_stub()
        make(stub, self.tmp.name).cycle()
        t2 = make(stub, self.tmp.name)
        self.assertGreater(len(t2.store), 0)
        self.assertEqual(t2.cycle()["new"], 0)

    def test_a_corrupt_line_and_an_unwritable_directory_do_not_break_it(self):
        p = Path(self.tmp.name) / "watch_events.jsonl"
        p.write_text('not json\n{"id": "w00000007", "kind": "info"}\n', encoding="utf-8")
        s = tower.EventStore(self.tmp.name)
        self.assertEqual(s.append(self.ev(0))["id"], "w00000008")
        blocker = Path(self.tmp.name) / "file"
        blocker.write_text("x")
        mem = tower.EventStore(blocker / "sub")  # cannot mkdir under a file
        self.assertIsNone(mem.path)
        mem.append(self.ev(1))
        self.assertEqual(len(mem), 1)


class AutoAssessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_auto_assess_is_off_by_default_and_starts_nothing(self):
        os.environ.pop("FF_AUTO_ASSESS", None)
        rt = FakeRuntime()
        t = tower.ControlTower(
            lambda: full_stub(), lambda: rt, data_dir=self.tmp.name, loop_enabled=False
        )
        self.assertFalse(t.auto_assess)
        t.cycle()
        self.assertEqual(rt.started, [])
        self.assertFalse(t.status()["auto_assess"]["enabled"])

    def test_switch_and_the_one_per_hour_cap(self):
        clock = Clock()
        rt = FakeRuntime()
        stub = full_stub()
        t = make(stub, self.tmp.name, runtime=lambda: rt, auto_assess=True, clock=clock)
        out = t.cycle()
        self.assertEqual(out["auto_assess_run_id"], "run1")
        self.assertEqual(len(rt.started), 1)
        req = rt.started[0]
        # the most severe new source: the gauge above MHW and the Loire are both "over"; ratio breaks the tie
        self.assertIn("Orleans", req.question)
        self.assertEqual(
            req.context.model_dump(exclude_none=True),
            {"role": "insurer", "page": "control-tower", "place": "Orleans", "auto": True},
        )
        self.assertEqual(
            router.route(req, None)["lane"], "full"
        )  # "insured sites" sends it to the full lane
        started = [e for e in t.store.all() if e["run_id"] == "run1"]
        self.assertEqual(len(started), 1)
        self.assertIn("model calls", started[0]["text"])
        # a new elevated source half an hour later: the hourly cap holds it back
        stub.rows["eu_watch"].append(
            eu("EU11", "Prague", "Vltava", "CZ", band="above", fmax=900, med=300)
        )
        clock.t += 1800
        self.assertEqual(t.cycle()["auto_assess_run_id"], None)
        self.assertEqual(len(rt.started), 1)
        self.assertEqual(t.auto_status()["used_hour"], 1)
        self.assertIsNotNone(t.auto_status()["next_allowed_at"])
        # after the hour the next new source may start one
        stub.rows["eu_watch"].append(
            eu("EU07", "Vienna", "Danube", "AT", band="above", fmax=2000, med=900)
        )
        clock.t += 3600
        self.assertEqual(t.cycle()["auto_assess_run_id"], "run2")

    def test_three_per_day_cap(self):
        clock = Clock()
        rt = FakeRuntime()
        stub = Stub(eus=[])
        t = make(stub, self.tmp.name, runtime=lambda: rt, auto_assess=True, clock=clock)
        ids = ["EU01", "EU02", "EU03", "EU04", "EU05"]
        started = []
        for pid in ids:
            stub.rows["eu_watch"].append(eu(pid, pid, "R", "FR", band="above"))
            clock.t += 3700  # outside the hourly window each time
            started.append(t.cycle()["auto_assess_run_id"])
        self.assertEqual(started, ["run1", "run2", "run3", None, None])
        self.assertEqual(t.auto_status()["used_day"], 3)
        clock.t += 86400
        stub.rows["eu_watch"].append(eu("EU06", "EU06", "R", "PL", band="above"))
        self.assertEqual(t.cycle()["auto_assess_run_id"], "run4")

    def test_caps_survive_a_restart(self):
        clock = Clock()
        rt = FakeRuntime()
        make(full_stub(), self.tmp.name, runtime=lambda: rt, auto_assess=True, clock=clock).cycle()
        self.assertEqual(len(rt.started), 1)
        stub = full_stub(
            eus=[eu("EU11", "Prague", "Vltava", "CZ", band="above", fmax=900, med=300)]
        )
        t2 = make(stub, self.tmp.name, runtime=lambda: rt, auto_assess=True, clock=clock)
        self.assertEqual(t2.auto_status()["used_hour"], 1)
        t2.cycle()
        self.assertEqual(len(rt.started), 1)

    def test_runtime_switch_never_approves_anything(self):
        rt = FakeRuntime()
        t = make(full_stub(), self.tmp.name, runtime=lambda: rt)
        self.assertFalse(t.auto_assess)
        t.set_auto_assess(True)
        self.assertTrue(t.auto_status()["enabled"])
        self.assertTrue(t.auto_status()["uses_model_calls"])
        self.assertFalse(hasattr(rt, "resume"))  # the tower has no way to approve
        t.set_auto_assess(False)
        t.cycle()
        self.assertEqual(rt.started, [])

    def test_manual_scan_is_rate_limited_and_never_overlaps(self):
        clock = Clock()
        t = make(full_stub(), self.tmp.name, clock=clock)
        self.assertTrue(t.force()["ran"])
        again = t.force()
        self.assertFalse(again["ran"])
        self.assertGreaterEqual(again["retry_after_s"], 1)
        clock.t += 10
        self.assertTrue(t.force()["ran"])
        t._cycle_lock.acquire()
        try:
            self.assertEqual(t.cycle()["reason"], "a scan is already running")
        finally:
            t._cycle_lock.release()

    def test_loop_switch(self):
        os.environ["FF_WATCH_LOOP"] = "false"
        try:
            t = tower.ControlTower(lambda: full_stub(), None, data_dir=self.tmp.name)
            self.assertFalse(t.loop_enabled)
            self.assertFalse(t.start())
        finally:
            os.environ.pop("FF_WATCH_LOOP", None)
        t = tower.ControlTower(lambda: full_stub(), None, data_dir=self.tmp.name, interval_s=300)
        self.assertTrue(t.loop_enabled)
        self.assertEqual(t.interval_s, 300)


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
        self.rt = Runtime(graph=build_graph(deps, MemorySaver(), ff_judge=True), deps=deps)
        service.set_runtime(self.rt)
        self.t = tower.ControlTower(
            lambda: self.rt.deps.zetaris,
            lambda: self.rt,
            data_dir=self.tmp.name,
            loop_enabled=False,
        )
        service.set_tower(self.t)
        self.addCleanup(lambda: service.set_tower(None))
        self.c = TestClient(service.app)

    def test_endpoints_status_events_cycle(self):
        r = self.c.post("/watch/cycle")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["cycle"]["ran"])
        self.assertEqual(self.c.post("/watch/cycle").status_code, 429)
        self.assertIn("Retry-After", self.c.post("/watch/cycle").headers)
        st = self.c.get("/watch/status").json()
        body = {k: v for k, v in st.items() if k != "label"}
        WatchStatus.model_validate(body)
        self.assertFalse(st["auto_assess"]["enabled"])
        self.assertEqual((st["auto_assess"]["per_hour"], st["auto_assess"]["per_day"]), (1, 3))
        self.assertIn("no model calls", st["note"])
        ev = self.c.get("/watch/events").json()
        self.assertEqual(ev["latest_id"], ev["events"][-1]["id"])
        for e in ev["events"]:
            WatchEvent.model_validate(e)
        self.assertEqual(self.c.get(f"/watch/events?since={ev['latest_id']}").json()["events"], [])
        self.assertEqual(len(self.c.get("/watch/events?limit=1").json()["events"]), 1)
        cfg = self.c.get("/config").json()
        self.assertEqual(cfg["watch"]["FF_AUTO_ASSESS"], False)
        self.assertEqual(cfg["watch"]["auto_assess_per_hour"], 1)
        self.assertNotIn(
            "FF_AUTO_ASSESS", cfg["flags"]
        )  # the flags are the API cache key; the switch moves

    def test_auto_assess_toggle(self):
        on = self.c.post("/watch/auto-assess", json={"enabled": True}).json()
        self.assertTrue(on["auto_assess"]["enabled"])
        self.assertTrue(self.c.get("/config").json()["watch"]["FF_AUTO_ASSESS"])
        off = self.c.post("/watch/auto-assess", json={"enabled": False}).json()
        self.assertFalse(off["auto_assess"]["enabled"])
        self.assertEqual(
            self.c.post("/watch/auto-assess", json={"enabled": "maybe"}).status_code, 422
        )

    def test_stream_sends_events_after_since_with_ids(self):
        self.t.emit("info", "first")
        self.t.emit("info", "second")
        service.STREAM_MAX_S, service.STREAM_POLL_S = 1.5, 0.2
        try:
            with self.c.stream("GET", "/watch/stream?since=w00000001") as s:
                text = "".join(s.iter_text())
        finally:
            service.STREAM_MAX_S, service.STREAM_POLL_S = 900, 1.0
        self.assertIn("id: w00000002\nevent: watch\n", text)
        self.assertIn('"text": "second"', text)
        self.assertNotIn('"text": "first"', text)

    def test_a_full_run_tells_the_whole_story_and_never_approves_itself(self):
        run = self.rt.start(
            RunRequest(
                question="Why are our Valencia sites at risk?",
                event_id="EMSR773",
                replay_ts="2024-10-29T18:00:00Z",
            )
        )
        self.assertEqual(run["status"], "awaiting_approval")
        kinds = [
            (e["kind"], e["agent"]) for e in self.t.store.all() if e["run_id"] == run["run_id"]
        ]
        self.assertEqual(kinds, [("drafted", "Playbook"), ("awaiting_approval", "Judge")])
        self.assertEqual(self.t.status()["counts"]["awaiting_approval"], 1)
        self.assertEqual(self.t.awaiting_run_ids(), [run["run_id"]])
        r = self.c.post(
            f"/runs/{run['run_id']}/approval", json={"action": "approve", "reviewer": "t"}
        )
        self.assertEqual(r.status_code, 200)
        kinds = [
            (e["kind"], e["agent"]) for e in self.t.store.all() if e["run_id"] == run["run_id"]
        ]
        self.assertEqual(kinds[-1], ("approved", "Human"))
        self.assertEqual(self.t.status()["counts"]["awaiting_approval"], 0)
        for e in self.t.store.all():
            WatchEvent.model_validate(e)

    def test_a_rejection_is_recorded_as_a_human_info_event(self):
        run = self.rt.start(
            RunRequest(
                question="Why are our Valencia sites at risk?",
                event_id="EMSR773",
                replay_ts="2024-10-29T18:00:00Z",
            )
        )
        self.c.post(
            f"/runs/{run['run_id']}/approval",
            json={"action": "reject", "reviewer_note": "no", "reviewer": "t"},
        )
        last = [e for e in self.t.store.all() if e["run_id"] == run["run_id"]][-1]
        self.assertEqual((last["kind"], last["agent"]), ("info", "Human"))
        self.assertIn("rejected", last["text"])
        self.assertEqual(self.t.awaiting_run_ids(), [])

    def test_a_quick_answer_adds_nothing(self):
        before = len(self.t.store)
        self.rt.observers[0]("paused", "does-not-exist")  # unknown run: ignored
        self.assertEqual(len(self.t.store), before)


class ObserverTest(unittest.TestCase):
    def test_an_observer_that_raises_does_not_break_a_run(self):
        deps = Deps(zetaris=FakeZetaris(), llm=FakeNightshift(), memory=NoMemory())
        rt = Runtime(graph=build_graph(deps, MemorySaver(), ff_judge=True), deps=deps)

        def boom(kind, run_id):
            raise RuntimeError("x")

        rt.observers.append(boom)
        run = rt.start(
            RunRequest(
                question="Why are our Valencia sites at risk?",
                event_id="EMSR773",
                replay_ts="2024-10-29T18:00:00Z",
            )
        )
        self.assertEqual(run["status"], "awaiting_approval")


if __name__ == "__main__":
    unittest.main()
