import { describe, expect, it } from "vitest";
import valencia from "../fixtures/valencia_points.json";
import type { ValenciaPoint } from "../types/views";
import {
  ahrDischarge,
  ahrMapPoints,
  boundsOf,
  DEFAULT_EVENT_ID,
  headerSubtitle,
  pointPopupText,
  valenciaMapPoints,
} from "./events";
import { ahrFixture } from "./replaySource";

describe("headerSubtitle", () => {
  it("is Live on the Now page whatever the event", () => {
    expect(headerSubtitle("now", "EMSR517")).toMatch(/^Live/);
    expect(headerSubtitle("now", "EMSR773")).toMatch(/^Live/);
  });
  it("names the selected replay event elsewhere", () => {
    expect(headerSubtitle("sites", "EMSR517")).toBe("Ahr 2021 replay · EMSR517");
    expect(headerSubtitle("replay", "EMSR773")).toBe("Valencia replay · EMSR773");
  });
  it("defaults to the Valencia views", () => {
    expect(DEFAULT_EVENT_ID).toBe("EMSR773");
  });
});

describe("event map points", () => {
  it("Ahr points are the seed AHR01-AHR04 with real coordinates, AHR04 labelled Dernau", () => {
    const points = ahrMapPoints();
    expect(points.map((p) => p.point_id)).toEqual(["AHR01", "AHR02", "AHR03", "AHR04"]);
    const dernau = points.find((p) => p.point_id === "AHR04");
    expect(dernau?.label).toBe("Dernau");
    expect(dernau?.lat).toBeCloseTo(50.53, 3);
    expect(dernau?.lon).toBeCloseTo(7.05, 3);
    for (const p of points) {
      expect(p.lat).toBeGreaterThan(50.4);
      expect(p.lat).toBeLessThan(50.6);
    }
  });

  it("Ahr discharge holds every point on the peak day", () => {
    const peak = ahrDischarge().filter((r) => r.date === "2021-07-14");
    expect(peak.map((r) => r.point_id).sort()).toEqual(["AHR01", "AHR02", "AHR03", "AHR04"]);
  });

  it("the replay fixture names AHR04 Dernau too", () => {
    expect(ahrFixture().points.find((p) => p.point_id === "AHR04")?.name).toBe("Dernau");
  });

  it("Valencia labels are the municipality, not the code", () => {
    const points = valenciaMapPoints(valencia as ValenciaPoint[]);
    expect(points.find((p) => p.point_id === "VAL01")?.label).toBe("Paiporta");
    expect(points.every((p) => !/^\d+$/.test(p.label))).toBe(true);
  });

  it("bounds wrap every point, null with none", () => {
    expect(boundsOf([])).toBeNull();
    expect(boundsOf([{ lat: 1, lon: 5 }, { lat: 3, lon: 2 }])).toEqual([
      [1, 2],
      [3, 5],
    ]);
  });

  it("popup text carries the code and the value", () => {
    const [p] = ahrMapPoints();
    expect(pointPopupText(p, 249.61, "14 Jul")).toBe("AHR01 · Altenahr · 249.6 m³/s on 14 Jul");
    expect(pointPopupText(p, null, "14 Jul")).toContain("no discharge row");
  });
});
