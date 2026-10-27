import { describe, expect, it } from "vitest";
import { adoptRunBody } from "../api/replay";
import { buildRunRequest } from "../api/ask";
import sample from "../fixtures/run_f16733274f1c.json";
import ahr from "../fixtures/ahr_2021.json";
import { buildPipeline, formatLatency, parseBoard, PIPELINE_ORDER } from "./pipeline";
import { buildRetrieval, cleanQuote } from "./retrieval";
import { mergeContext, withAskContext } from "./askContext";
import {
  buildFrames,
  clampStep,
  crossings,
  dayStarts,
  momentQuestion,
  nextStep,
  readingsAt,
  REPLAY_EVENTS,
  replayLabel,
  type ReplayReading,
} from "./disasterReplay";

const run = adoptRunBody(sample as unknown as Record<string, unknown>, "f16733274f1c")!;

describe("buildPipeline", () => {
  it("keeps the canonical node order and folds world_model into badges", () => {
    const model = buildPipeline(run);
    expect(model.nodes.map((n) => n.id)).toEqual([...PIPELINE_ORDER]);
    expect(model.nodes.some((n) => (n.id as string) === "world_model")).toBe(false);
  });

  it("shows the revise and repair loops from the run", () => {
    const model = buildPipeline(run);
    expect(model.reviseRounds).toBe(1);
    expect(model.repairRounds).toBe(1);
    const skeptic = model.nodes.find((n) => n.id === "skeptic")!;
    expect(skeptic.runs).toBe(2); // the revise edge step is not a run
    expect(skeptic.latencyMs).toBe(126328 + 181928);
    expect(model.nodes.find((n) => n.id === "judge")!.status).toBe("flag");
    expect(model.nodes.find((n) => n.id === "approval")!.status).toBe("waiting");
  });

  it("puts sponsor badges where they apply", () => {
    const model = buildPipeline(run);
    const badges = (id: string) => model.nodes.find((n) => n.id === id)!.badges.map((b) => b.text);
    expect(badges("watchers")).toEqual(["Zetaris · 3 queryIds"]);
    expect(badges("memory")).toEqual(["H-MEM recall"]);
    expect(badges("skeptic")).toContain("Nightshift · answered by Nemotron 3.5 Lightning 30B A3B");
    expect(badges("skeptic").some((t) => t.startsWith("World Model · H1 not_supported"))).toBe(true);
    expect(badges("investigator")).toContain("pgvector + Zetaris JDBC");
    expect(badges("scope")).toEqual([]);
    expect(model.board?.states).toEqual([
      { id: "H1", state: "not_supported" },
      { id: "H2", state: "supported" },
      { id: "H3", state: "supported" },
    ]);
  });

  it("shows a non-Nightshift model as its id and survives a bare body", () => {
    const bare = adoptRunBody(
      {
        served_from: "live",
        summary: "s",
        claims: [],
        trace: [{ seq: 1, node: "investigator", lane: "fast", model_id: "anthropic/claude-sonnet-5-5", latency_ms: 900 }],
      },
      "x",
    )!;
    const model = buildPipeline(bare);
    expect(model.reviseRounds).toBe(0);
    expect(model.nodes.find((n) => n.id === "investigator")!.badges).toEqual([{ kind: "model", text: "anthropic/claude-sonnet-5-5" }]);
    expect(model.nodes.find((n) => n.id === "watchers")!.status).toBe("skipped");
  });

  it("parses boards and latencies", () => {
    expect(parseBoard("board after investigator: H1 proposed, H2 supported")?.states).toHaveLength(2);
    expect(parseBoard("0 anomalies observed")).toBeNull();
    expect(formatLatency(null)).toBe("—");
    expect(formatLatency(980)).toBe("980 ms");
    expect(formatLatency(149338)).toBe("2 min 29 s");
  });
});

describe("buildRetrieval", () => {
  it("groups layer (c) passages per claim with the Judge verdict and the flag", () => {
    const model = buildRetrieval(run);
    expect(model.groups.map((g) => g.claimId)).toEqual(["C-doc"]);
    const g = model.groups[0];
    expect(g.passages.length).toBe(model.passageCount);
    expect(g.flagged).toBe(true);
    expect(g.verdict?.grounding).toBe("unsupported");
    expect(model.query).toBe("Barranc del Poyo flash flood Paiporta Horta Sud delineation");
    expect(g.passages[0].page).toBe(3);
  });

  it("drops map-symbol noise and trims long quotes", () => {
    expect(cleanQuote("!\n!\n!!\n! !")).toBeNull();
    expect(cleanQuote("a ".repeat(400), 20)?.length).toBeLessThanOrEqual(20);
    expect(cleanQuote(null)).toBeNull();
  });
});

describe("ask context", () => {
  it("adds a clean context only when enabled", () => {
    expect(withAskContext({ q: 1 }, { page: "replay", place: " " }, true)).toEqual({ q: 1, context: { page: "replay" } });
    expect(withAskContext({ q: 1 }, { page: "replay" }, false)).toEqual({ q: 1 });
    expect(withAskContext({ q: 1 }, null, true)).toEqual({ q: 1 });
    expect(mergeContext({ role: "insurer", page: "sites" }, { page: "replay", event_id: "EMSR517" })).toEqual({
      role: "insurer",
      page: "replay",
      event_id: "EMSR517",
    });
  });

  it("rides on the run request", () => {
    const body = buildRunRequest({
      question: "q",
      provider: "nightshift",
      allowedProviders: [],
      context: { page: "replay", event_id: "EMSR517", replay_date: "2021-07-14T18:00:00Z" },
    });
    expect(body.context).toEqual({ page: "replay", event_id: "EMSR517", replay_date: "2021-07-14T18:00:00Z" });
  });
});

describe("disaster replay timeline", () => {
  const ahrEvent = REPLAY_EVENTS[0];
  const rows = ahr.hazard_timeline as ReplayReading[];

  it("steps hourly through the Ahr window, one day stop each", () => {
    const frames = buildFrames(rows, ahrEvent);
    expect(frames.length).toBe(96);
    expect(frames[0]).toBe("2021-07-13T00:00:00Z");
    expect(dayStarts(frames).map((d) => d.index)).toEqual([0, 24, 48, 72]);
    expect(clampStep(-3, 96)).toBe(0);
    expect(clampStep(200, 96)).toBe(95);
    expect(nextStep(95, 96)).toBe(0);
    expect(readingsAt(rows, frames[30]).size).toBe(3);
  });

  it("marks the moment discharge crosses the line", () => {
    const frames = buildFrames(rows, ahrEvent);
    const c = crossings(rows, frames, ahrEvent.thresholdM3s).get("AHR01");
    expect(c?.iso).toBe("2021-07-14T00:00:00Z");
    expect(c && c.discharge).toBeGreaterThanOrEqual(100);
  });

  it("reads zone-less view stamps and labels the replay", () => {
    const view: ReplayReading[] = [
      { point_id: "V", ts_utc: "2024-10-29 00:00:00.0", rain_mm: 0, discharge_m3s: 30 },
      { point_id: "V", ts_utc: "2024-10-30 00:00:00.0", rain_mm: 9, discharge_m3s: 400 },
      { point_id: "V", ts_utc: "2024-11-02 00:00:00.0", rain_mm: 0, discharge_m3s: 50 },
    ];
    const frames = buildFrames(view, REPLAY_EVENTS[1]);
    expect(frames).toEqual(["2024-10-29T00:00:00Z", "2024-10-30T00:00:00Z"]);
    expect(crossings(view, frames, 100).get("V")?.index).toBe(1);
    expect(replayLabel(REPLAY_EVENTS[1])).toBe("Replay of Valencia DANA, 28–31 Oct 2024 · not live");
    expect(momentQuestion("Altenahr", "2021-07-14T18:00:00Z")).toBe("Why was Altenahr at risk on 14 Jul 2021 at 18:00 UTC?");
  });
});
