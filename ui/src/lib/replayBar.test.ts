import { describe, expect, it } from "vitest";
import { replayBarView } from "./events";

const valencia = { date: "2024-10-29" };
const ahr = { date: "2021-07-14" };

describe("replayBarView (context strip)", () => {
  it("says Live data on Now, on both desks", () => {
    expect(replayBarView({ role: "citizen", page: "now" }, "EMSR773", valencia, ahr)).toEqual({ kind: "live", text: "Live data" });
    expect(replayBarView({ role: "insurer", page: "now" }, "EMSR517", valencia, ahr).text).toBe("Live data");
  });

  it("names Valencia plainly on citizen Overview and My area", () => {
    for (const page of ["overview", "area"] as const) {
      const v = replayBarView({ role: "citizen", page }, "EMSR517", valencia, ahr);
      expect(v.text).toBe("Viewing: Valencia flood · 29 Oct 2024 (replay of a past event)");
    }
  });

  it("follows the selected event on Replay and Sites", () => {
    expect(replayBarView({ role: "insurer", page: "sites" }, "EMSR517", valencia, ahr).text).toBe(
      "Viewing: Ahr flood · 14 Jul 2021 (replay of a past event)",
    );
    expect(replayBarView({ role: "insurer", page: "replay" }, "EMSR773", valencia, ahr).text).toBe(
      "Viewing: Valencia flood · 29 Oct 2024 (replay of a past event)",
    );
    expect(replayBarView({ role: "citizen", page: "replay" }, "EMSR517", valencia, ahr).kind).toBe("replay");
  });

  it("shows nothing on pages without a replayed event", () => {
    for (const page of ["approvals", "portfolio", "alerts", "review", "how"] as const) {
      expect(replayBarView({ role: "insurer", page }, "EMSR773", valencia, ahr)).toEqual({ kind: "none", text: "" });
    }
    for (const page of ["actions", "evidence", "how"] as const) {
      expect(replayBarView({ role: "citizen", page }, "EMSR773", valencia, ahr).kind).toBe("none");
    }
  });
});
