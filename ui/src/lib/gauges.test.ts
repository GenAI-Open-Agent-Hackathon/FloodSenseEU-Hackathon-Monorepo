import { describe, expect, it } from "vitest";
import { fetchGaugeLevels } from "../api/gauges";
import { asGaugeRow, stationPosition, summariseGauges } from "./gauges";

const row = (station: string, ts: string, level: number) => ({
  station,
  water: "RHEIN",
  ts_utc: ts,
  level_cm: level,
  source: "pegelonline",
});

describe("gauge_levels rows", () => {
  it("parses the view columns and rejects bad rows", () => {
    expect(asGaugeRow(row("BONN", "2026-10-27 10:00:00", 312))?.ts_utc).toBe("2026-10-27T10:00:00Z");
    expect(asGaugeRow({ station: "BONN", ts_utc: "x", level_cm: 1 })).toBeNull();
    expect(asGaugeRow({ station: "", ts_utc: "2026-10-27T10:00:00Z", level_cm: 1 })).toBeNull();
  });

  it("keeps the latest reading per station with a trend, and never invents a threshold", () => {
    const rows = [row("BONN", "2026-10-27T09:00:00Z", 300), row("BONN", "2026-10-27T10:00:00Z", 310), row("KÖLN", "2026-10-27T10:00:00Z", 280)]
      .map(asGaugeRow)
      .filter((r) => r !== null);
    const out = summariseGauges(rows);
    const bonn = out.find((g) => g.station === "BONN");
    expect(bonn?.levelCm).toBe(310);
    expect(bonn?.trend).toBe("rising");
    expect(bonn?.status).toBe("unknown");
    expect(bonn?.warningLevelCm).toBeNull();
    expect(out.find((g) => g.station === "KÖLN")?.trend).toBeNull();
  });

  it("places known stations, folding umlauts", () => {
    expect(stationPosition("Köln")).not.toBeNull();
    expect(stationPosition("KOELN")).toEqual(stationPosition("Köln"));
    expect(stationPosition("Nowhere")).toBeNull();
  });
});

describe("fetchGaugeLevels", () => {
  const respond = (body: unknown, status = 200) =>
    (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

  it("reports an empty view as empty, not live", async () => {
    expect((await fetchGaugeLevels(undefined, respond([]))).state).toBe("empty");
  });
  it("reports rows as live", async () => {
    const load = await fetchGaugeLevels(undefined, respond([row("BONN", "2026-10-27T10:00:00Z", 1)]));
    expect(load.state).toBe("live");
    expect(load.rows).toHaveLength(1);
  });
  it("reports errors and bad shapes as unavailable", async () => {
    expect((await fetchGaugeLevels(undefined, respond([], 500))).state).toBe("unavailable");
    expect((await fetchGaugeLevels(undefined, respond({ rows: [] }))).state).toBe("unavailable");
  });
});
