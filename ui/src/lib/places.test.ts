import { describe, expect, it } from "vitest";
import { fromGauge, fromModel, fromValencia, type WatchSource } from "./euWatch";
import type { GaugeSummary } from "./gauges";
import {
  basisLabel,
  buildPlaces,
  calmSentence,
  plainStatus,
  questionForPlace,
  replayEventOfPlace,
  searchPlaces,
  statusCounts,
  worstFirst,
} from "./places";
import { humanBox } from "./howItWorks";

const gauge = (station: string, water: string, status: GaugeSummary["status"], level = 300, mhw = 500): GaugeSummary => ({
  station,
  water,
  levelCm: level,
  measuredAt: "2026-10-27T10:00:00Z",
  trend: "steady",
  history: [],
  source: "pegelonline",
  status,
  warningLevelCm: mhw,
  meanLevelCm: 200,
  stale: false,
  origin: "live",
  lat: 50.9,
  lon: 6.9,
});

const model = (point_id: string, name: string, river: string, country: string, band: "ok" | "near" | "over") =>
  fromModel({
    point_id,
    name,
    country,
    river,
    lat: 47.5,
    lon: 19,
    discharge_m3s: 2000,
    forecast_max_m3s: 2500,
    past30_median_m3s: 1000,
    band,
    basis: "",
    source: "open-meteo-flood-glofas",
    as_of_date: "2026-10-27",
  });

const sources: WatchSource[] = [
  fromGauge(gauge("KÖLN", "RHEIN", "near", 420))!,
  fromGauge(gauge("DRESDEN", "ELBE", "ok"))!,
  fromGauge(gauge("PASSAU DONAU", "DONAU", "over", 700))!,
  model("EU05", "Budapest", "Danube", "HU", "ok"),
  model("EU01", "Paris", "Seine", "FR", "near"),
  fromValencia({ point_id: "VAL01", name: "Paiporta centre", lat: 39.4, lon: -0.4 }, { latest: { discharge_m3s: 2, ts_utc: "2026-10-27T09:00:00Z" }, forecastMax: { discharge_m3s: 3 } }, { watch: 20, warning: 80 }),
];

const places = buildPlaces(
  sources,
  [{ point_id: "VAL01", name: "Paiporta centre", municipality: "Paiporta" }],
  [{ point_id: "AHR01", name: "Altenahr" }],
);

describe("plain status mapping", () => {
  it("maps the view bands to Normal / Watch / Warning", () => {
    expect(plainStatus("ok")).toBe("normal");
    expect(plainStatus("near")).toBe("watch");
    expect(plainStatus("over")).toBe("warning");
    expect(plainStatus("unknown")).toBe("unknown");
  });
  it("labels the model and the official threshold differently", () => {
    expect(basisLabel("gauge")).toMatch(/official gauge threshold \(MHW\)/);
    expect(basisLabel("model")).toMatch(/model, not an official warning/);
    expect(basisLabel("valencia")).toMatch(/not official/);
  });
  it("uses one calm sentence without numbers", () => {
    const s = calmSentence("gauge", "watch", "Rhine", "Köln");
    expect(s).toMatch(/^The Rhine at Köln is higher than usual/);
    expect(s).not.toMatch(/\d/);
    expect(calmSentence("model", "normal", "Danube", "Budapest")).toMatch(/Our model/);
    expect(calmSentence("gauge", "unknown", "Rhine", "Köln")).toMatch(/no current reading/);
  });
  it("sorts worst first and counts", () => {
    const order = worstFirst(sources).map((s) => s.name);
    expect(order[0]).toBe("Passau Donau");
    expect(order.slice(1, 3).sort()).toEqual(["Köln", "Paris"]);
    expect(statusCounts(sources)).toEqual({ warning: 1, watch: 2, normal: 3, unknown: 0 });
  });
  it("bands Valencia points by the demo lines", () => {
    const v = (q: number) =>
      fromValencia({ point_id: "VAL02", name: "x", lat: 0, lon: 0 }, { latest: { discharge_m3s: q, ts_utc: "t" }, forecastMax: null }, { watch: 20, warning: 80 }).status;
    expect([v(5), v(25), v(90)]).toEqual(["ok", "near", "over"]);
  });
});

describe("place search", () => {
  it("covers gauges, EU points and replay places", () => {
    expect(places).toHaveLength(sources.length + 2);
    expect(searchPlaces(places, "koln").map((p) => p.name)).toEqual(["Köln"]);
    expect(searchPlaces(places, "danube").map((p) => p.name).sort()).toEqual(["Budapest", "Passau Donau"]);
    expect(searchPlaces(places, "hungary").map((p) => p.name)).toEqual(["Budapest"]);
    expect(searchPlaces(places, "paiporta").map((p) => p.id)).toEqual(["valencia:VAL01", "replay:VAL01"]);
    expect(searchPlaces(places, "ahr").map((p) => p.id)).toEqual(["replay:AHR01"]);
    expect(searchPlaces(places, "")).toHaveLength(places.length);
    expect(searchPlaces(places, "atlantis")).toEqual([]);
  });
  it("knows the replay event and the Ask question of a place", () => {
    expect(replayEventOfPlace("replay:VAL01")).toBe("EMSR773");
    expect(replayEventOfPlace("replay:AHR01")).toBe("EMSR517");
    expect(replayEventOfPlace("gauge:KÖLN")).toBeNull();
    expect(replayEventOfPlace(null)).toBeNull();
    expect(questionForPlace(places.find((p) => p.name === "Köln")!)).toBe("Is the Rhine at Köln at risk right now?");
    expect(questionForPlace(places.find((p) => p.id === "replay:AHR01")!)).toMatch(/Ahr flood of July 2021/);
  });
  it("gives each place its country", () => {
    expect(places.find((p) => p.name === "Köln")!.country).toBe("DE");
    expect(places.find((p) => p.name === "Paris")!.country).toBe("FR");
    expect(places.find((p) => p.id === "replay:VAL01")!.country).toBe("ES");
  });
});

describe("How it works human box", () => {
  it("is reworded for citizens and kept for insurers", () => {
    expect(humanBox("citizen").line).toBe("Insurer alerts are checked by a person before they're sent. Your answers aren't held back.");
    expect(humanBox("insurer").title).toBe("Human approval");
  });
});
