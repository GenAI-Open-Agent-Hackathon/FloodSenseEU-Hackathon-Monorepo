import { describe, expect, it } from "vitest";
import { fixtureDischargeNotice, seedRowsNotice } from "./notices";
import type { DischargeDailyRow } from "../types/views";

const row: DischargeDailyRow = {
  point_id: "VAL01",
  date: "2024-10-29",
  discharge_m3s: 31.06,
  source: "seed:open-meteo-flood-glofas",
};

describe("discharge notices", () => {
  it("gives the fixture notice its own id", () => {
    const notice = fixtureDischargeNotice([row]);
    expect(notice.id).toBe("fixture-loaded");
    expect(notice.title).toMatch(/fixture/i);
    expect(notice.body).not.toMatch(/\bseed rows\b/i);
  });

  it("keeps the seed notice for a seed origin", () => {
    const notice = seedRowsNotice([row]);
    expect(notice.id).toBe("seed-loaded");
    expect(notice.body).toMatch(/These rows are seed/);
  });
});
