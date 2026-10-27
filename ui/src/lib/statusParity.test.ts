import { describe, expect, it } from "vitest";
import cases from "../../../contracts/examples/status_cases.json";
import { asEuWatchRow, fromValencia } from "./euWatch";
import { asGaugeRow } from "./gauges";
import { statusView } from "./places";

/** The control tower (agents tower.py) reads the same file, so a plain status means one thing in both. */
describe("status parity with the control tower (contracts/examples/status_cases.json)", () => {
  it("words, tones and ranks", () => {
    // Valencia is excluded on purpose: the UI measures those points against their own recent flow (#90 review H2,
    // `valenciaCuts`), while agents tower.py still uses the 20 / 80 m³/s demo lines. Align tower.py and the contract file next.
    for (const c of cases.words.filter((w) => w.kind !== "valencia")) {
      const v = statusView(c.kind as "gauge" | "model" | "valencia", c.status as "ok" | "near" | "over" | "unknown");
      expect({ word: v.word, tone: v.tone, rank: v.rank }).toEqual({ word: c.word, tone: c.tone, rank: c.rank });
    }
  });

  it("a gauge row: its band, and a missing is_stale means stale", () => {
    for (const c of cases.gauge_rows) {
      const row = asGaugeRow(c.row);
      expect(row, c.name).not.toBeNull();
      expect(row!.is_stale, c.name).toBe(c.stale);
      expect(row!.band, c.name).toBe(c.band_status);
      // what the tower turns into an event: a stale reading is never one
      expect(row!.is_stale ? "unknown" : row!.band, c.name).toBe(c.event_status);
    }
  });

  it("a model band: an unknown band stays unknown", () => {
    for (const c of cases.model_bands) {
      const row = asEuWatchRow({ point_id: "EU01", name: "Paris", lat: 48.9, lon: 2.3, river: "Seine", country: "FR", band: c.band });
      expect(row?.band, c.band).toBe(c.status);
    }
  });

  it("a Valencia point keeps its status against its own cuts (the contract's 20 / 80 lines are not used here)", () => {
    const at = (q: number) =>
      fromValencia(
        { point_id: "VAL01", name: "Paiporta", lat: 39.4, lon: -0.4 },
        { latest: { discharge_m3s: q, ts_utc: "2026-10-27T12:00:00Z" }, forecastMax: null },
        { watch: 60, warning: 120 },
      ).status;
    expect([at(30), at(60), at(120)]).toEqual(["ok", "near", "over"]);
  });
});
