import { describe, expect, it } from "vitest";
import { adoptView, markBatchSeed } from "./adopt";

const fixture = [{ point_id: "VAL01" }];
const fixtureDetail = "Fixture copy.";

describe("adoptView", () => {
  it("keeps the fixture when health failed", () => {
    const adopted = adoptView({
      healthOk: false,
      parsed: [{ point_id: "LIVE" }],
      fixtureRows: fixture,
      fixtureDetail,
      missDetail: "ignored",
    });
    expect(adopted.origin).toBe("fixture");
    expect(adopted.rows).toEqual(fixture);
    expect(adopted.detail).toBe(fixtureDetail);
  });

  it("keeps the fixture when the body is not a valid array", () => {
    const adopted = adoptView({
      healthOk: true,
      parsed: null,
      fixtureRows: fixture,
      fixtureDetail,
      missDetail: "GET /views/discharge_daily did not match the view columns",
    });
    expect(adopted.origin).toBe("fixture");
    expect(adopted.rows).toEqual(fixture);
    expect(adopted.detail).toContain("did not match");
  });

  it("adopts an empty array as live with zero rows", () => {
    const adopted = adoptView({
      healthOk: true,
      parsed: [],
      fixtureRows: fixture,
      fixtureDetail,
      missDetail: "GET /views/discharge_daily",
    });
    expect(adopted.origin).toBe("live");
    expect(adopted.rows).toEqual([]);
    expect(adopted.detail).toContain("0 rows");
  });

  it("adopts valid rows as live", () => {
    const rows = [{ point_id: "LIVE" }];
    const adopted = adoptView({
      healthOk: true,
      parsed: rows,
      fixtureRows: fixture,
      fixtureDetail,
      missDetail: "GET /views/discharge_daily",
    });
    expect(adopted.origin).toBe("live");
    expect(adopted.rows).toEqual(rows);
    expect(adopted.detail).toContain("GET /views/discharge_daily");
  });

  it("does not label a mix of seed and non-seed rows as live", () => {
    const adopted = adoptView({
      healthOk: true,
      parsed: [{ source: "seed:open-meteo-flood-glofas" }, { source: "open-meteo-flood-glofas" }],
      fixtureRows: [{ source: "seed:fixture" }],
      fixtureDetail,
      missDetail: "GET /views/discharge_daily",
    });
    expect(adopted.origin).toBe("seed");
    expect(adopted.detail).not.toMatch(/\blive\b/);
  });

  it("labels seed-stamped view rows as seed, not live", () => {
    const adopted = adoptView({
      healthOk: true,
      parsed: [{ source: "seed:open-meteo-flood-glofas" }],
      fixtureRows: [{ source: "seed:fixture" }],
      fixtureDetail,
      missDetail: "GET /views/discharge_daily",
    });
    expect(adopted.origin).toBe("seed");
    expect(adopted.detail).not.toMatch(/\blive\b/);
  });

  it("does not treat a health success with no view body as live", () => {
    const adopted = adoptView({
      healthOk: true,
      parsed: null,
      fixtureRows: fixture,
      fixtureDetail,
      missDetail: "GET /views/discharge_daily returned 404",
    });
    expect(adopted.origin).toBe("fixture");
  });

  it("marks sibling view responses seed when discharge is seed", () => {
    const discharge = adoptView({
      healthOk: true,
      parsed: [{ source: "seed:open-meteo-flood-glofas" }],
      fixtureRows: [{ source: "seed:fixture" }],
      fixtureDetail,
      missDetail: "GET /views/discharge_daily",
    });
    const hazard = markBatchSeed(
      discharge,
      adoptView({
        healthOk: true,
        parsed: [{ point_id: "VAL01" }],
        fixtureRows: [],
        fixtureDetail,
        missDetail: "GET /views/hazard_timeline",
      }),
    );
    expect(hazard.origin).toBe("seed");
    expect(hazard.detail).toBe("GET /views/hazard_timeline · seed");
    expect(hazard.detail).not.toMatch(/\blive\b/);
  });
});
