import { describe, expect, it } from "vitest";
import { originPill } from "./origin";

const live = ["live", "live", "live", "live"] as const;

describe("originPill", () => {
  it("labels a fully live seed discharge as API seed rows", () => {
    expect(
      originPill([...live], {
        origin: "live",
        rows: [{ source: "seed:open-meteo-flood-glofas" }],
      }).label,
    ).toBe("API · seed rows");
  });

  it("labels other live rows as live view rows", () => {
    expect(
      originPill([...live], {
        origin: "live",
        rows: [{ source: "open-meteo-flood-glofas" }],
      }).label,
    ).toBe("Live view rows");
  });

  it("stays on the fixture label when nothing is live", () => {
    expect(originPill(["fixture", "fixture", "fixture", "fixture"]).label).toBe("Fixture · not live");
  });
});
