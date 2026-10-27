import { describe, expect, it } from "vitest";
import { formatDay } from "./format";
import { replayBarView } from "./events";

const valencia = { date: "2024-10-29", pointId: "VAL01", points: [{ point_id: "VAL01", name: "Paiporta centre" }] };
const ahr = { date: "2021-07-14", pointId: "AHR01" };

describe("replayBarView", () => {
  it("follows Ahr on Sites and Replay", () => {
    for (const page of ["sites", "replay"] as const) {
      const v = replayBarView({ role: "insurer", page }, "EMSR517", valencia, ahr, false);
      expect(`${formatDay(v.date)} · ${v.place}`).toBe("14 Jul 2021 · AHR01 Altenahr");
      expect(v.playback).toBe("none");
    }
  });

  it("names a running Valencia simulation on an Ahr page instead of claiming Ahr plays", () => {
    const v = replayBarView({ role: "insurer", page: "sites" }, "EMSR517", valencia, ahr, true);
    expect(v.playback).toBe("valencia-elsewhere");
    expect(v.date).toBe("2021-07-14");
  });

  it("shows Valencia when Valencia is the selected event", () => {
    const v = replayBarView({ role: "insurer", page: "sites" }, "EMSR773", valencia, ahr, true);
    expect(v).toEqual({ date: "2024-10-29", place: "VAL01 Paiporta centre", playback: "valencia" });
  });

  it("keeps Valencia on pages that show no event", () => {
    const v = replayBarView({ role: "insurer", page: "alerts" }, "EMSR517", valencia, ahr, false);
    expect(v).toEqual({ date: "2024-10-29", place: "VAL01 Paiporta centre", playback: "valencia" });
  });

  it("falls back to the bare point id when the point is unknown", () => {
    const v = replayBarView({ role: "insurer", page: "alerts" }, "EMSR517", { ...valencia, pointId: "VAL99" }, ahr, false);
    expect(v.place).toBe("VAL99");
  });
});