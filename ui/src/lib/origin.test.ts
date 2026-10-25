import { describe, expect, it } from "vitest";
import { originPill, statusLabel } from "./origin";

describe("originPill", () => {
  it("labels a seed desk as seed, without the live tone", () => {
    const pill = originPill(["seed", "seed", "seed", "seed"]);
    expect(pill).toEqual({ tone: "seed", label: "Seed" });
    expect(pill.tone).not.toBe("live");
  });

  it("labels a non-seed view response as live", () => {
    expect(originPill(["live", "live", "live", "live"])).toEqual({ tone: "live", label: "Live" });
  });

  it("labels fixtures as fixture", () => {
    const pill = originPill(["fixture", "fixture", "fixture", "fixture"]);
    expect(pill).toEqual({ tone: "fixture", label: "Fixture" });
    expect(pill.label.toLowerCase()).not.toContain("live");
  });

  it("names a seed and fixture mix without calling it live", () => {
    const pill = originPill(["seed", "fixture", "fixture", "seed"]);
    expect(pill.tone).toBe("mixed");
    expect(pill.label).toBe("Seed · Fixture");
    expect(pill.label).not.toMatch(/live/i);
  });
});

describe("statusLabel", () => {
  it("uses Fixture, Seed, and Live", () => {
    expect(statusLabel("fixture")).toBe("Fixture");
    expect(statusLabel("seed")).toBe("Seed");
    expect(statusLabel("live")).toBe("Live");
  });
});
