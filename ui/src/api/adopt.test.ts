import { describe, expect, it } from "vitest";
import { adoptView } from "./adopt";

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
    expect(adopted).toEqual({
      rows,
      origin: "live",
      detail: "GET /views/discharge_daily",
    });
  });
});
