import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ImpactStrip } from "../components/ImpactStrip";
import type { WatchSource } from "./euWatch";
import { citizenChips, GOALS, insurerChips, operatorChips } from "./impact";

const src = (status: WatchSource["status"]) => ({ id: status, status, kind: "gauge" }) as unknown as WatchSource;
const row = (inside: boolean, sum: number) => ({ policy_id: "p", site_id: "s", lat: 0, lon: 0, in_footprint: inside, sum_insured_eur: sum, segment: "x" });

describe("impact chips", () => {
  it("citizen: null without sources, counts otherwise", () => {
    expect(citizenChips([]).every((c) => c.value === null)).toBe(true);
    expect(citizenChips([src("ok"), src("near"), src("over")]).map((x) => x.value)).toEqual(["3", "2"]);
  });
  it("insurer: null without rows, sums exposed policies", () => {
    expect(insurerChips([], 0).every((c) => c.value === null)).toBe(true);
    expect(insurerChips([row(true, 100), row(false, 50)], 45).map((x) => x.value)).toEqual(["1 of 2", "EUR 100", "45"]);
  });
  it("operator: pending null stays null, zero stays 0", () => {
    expect(operatorChips([], 0, null).every((c) => c.value === null)).toBe(true);
    expect(operatorChips([src("over"), src("ok")], 10, 0).map((x) => x.value)).toEqual(["1", "10", "0"]);
  });
});

describe("ImpactStrip", () => {
  it("renders goal, no data yet and the cited fact", () => {
    const html = renderToStaticMarkup(createElement(ImpactStrip, { goal: GOALS.citizen, chips: citizenChips([]), fact: { text: "T", source: "S" } }));
    expect(html).toContain("no data yet");
    expect(html).toContain(GOALS.citizen);
    expect(html).toContain("Source: S");
  });
});
