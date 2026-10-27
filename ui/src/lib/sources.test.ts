import { describe, expect, it } from "vitest";
import { adoptRunBody } from "../api/replay";
import sample from "../fixtures/run_f16733274f1c.json";
import answer from "../fixtures/answer.json";
import type { Answer } from "../types/contract";
import { memoryLabel, sourceFromCitation, sourceFromRun, upstreamFor } from "./sources";
import { modelChip, runModelLine } from "./modelChip";
import { buildPipeline } from "./pipeline";

const run = adoptRunBody(sample as unknown as Record<string, unknown>, "f16733274f1c")!;
const all = run.claims.flatMap((c) => c.citations);

describe("grounded sources", () => {
  it("Zetaris data shows the view, the query id and the upstream feed link", () => {
    const a = all.find((c) => c.layer === "a" && c.title.includes("discharge_daily"))!;
    const d = sourceFromRun(a, "EMSR773");
    expect(d.heading).toBe("Data via Zetaris");
    expect(d.facts).toContain("View floodsense.discharge_daily");
    expect(d.facts.some((f) => f.startsWith("Query id 1223e572"))).toBe(true);
    expect(d.link?.href).toBe("https://open-meteo.com/en/docs/flood-api");
    expect(upstreamFor("floodsense.exposure_join", "EMSR517")?.href).toMatch(/EMSR517$/);
    expect(upstreamFor("floodsense.gauge_levels")?.label).toBe("WSV PEGELONLINE");
  });

  it("a document shows title, publisher, page and paragraph, quote and the source URL", () => {
    const c = all.find((x) => x.layer === "c" && x.chunkId === "hess-29-6715-2025/p3/para1")!;
    const d = sourceFromRun(c, "EMSR773");
    expect(d.kind).toBe("document");
    expect(d.facts).toEqual(["Copernicus Publications", "Page 3, paragraph 1"]);
    expect(d.link?.href).toBe("https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf");
  });

  it("contract citations on Overview link to their source; seed views say so", () => {
    const first = (answer as unknown as Answer).citations[0];
    const d = sourceFromCitation(first, "EMSR773");
    expect(d.link?.href).toMatch(/^https:\/\/open-meteo\.com/);
    expect(d.facts).toContain("Seed data (recorded rows)");
  });

  it("memory labels name the approving run, or the demo seed", () => {
    expect(memoryLabel({ runId: "r42" })).toBe("H-MEM · approved run r42");
    expect(memoryLabel({ runId: null })).toBe("H-MEM · Demo seed");
  });
});

describe("model chip", () => {
  it("names the model and the Nightshift lane", () => {
    expect(modelChip("nvidia/nemotron-3.5-lightning-30b-a3b", "fast")).toBe("Nemotron 3.5 Lightning 30B · Nightshift fast lane");
    expect(modelChip("deterministic,nvidia/nemotron-3.5-lightning-30b-a3b", "deep")).toBe(
      "Nemotron 3.5 Lightning 30B · Nightshift deep lane",
    );
    expect(modelChip(null, "sql")).toBe("SQL · Zetaris");
    expect(modelChip("deterministic", "none")).toBe("rules");
    expect(modelChip("claude-sonnet-x", "fast")).toBe("claude-sonnet-x");
    expect(runModelLine(run.trace.map((s) => s.modelId ?? ""))).toBe("Nemotron 3.5 Lightning 30B via Nightshift");
  });
});

describe("router node", () => {
  it("is drawn first only when the trace has one", () => {
    expect(buildPipeline(run).nodes[0].id).toBe("scope");
    const routed = { ...run, trace: [{ seq: 0, node: "router", summary: "lane full", lane: "fast" }, ...run.trace] };
    expect(buildPipeline(routed).nodes[0].id).toBe("router");
  });
});
