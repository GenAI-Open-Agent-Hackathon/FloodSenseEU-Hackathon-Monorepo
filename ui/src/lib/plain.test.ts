import { describe, expect, it } from "vitest";
import { plainLanguage } from "./plain";

describe("plainLanguage", () => {
  it("replaces table and column names but keeps the numbers", () => {
    const out = plainLanguage(
      "VAL07 discharge in floodsense_seed.discharge_daily is 0.62 m³/s on 29 Oct 2024. The source column is seed:open-meteo-flood-glofas. warning_level is null.",
    );
    expect(out).not.toMatch(/floodsense_seed|warning_level|source column/);
    expect(out).toContain("0.62 m³/s");
    expect(out).toContain("no official warning level is attached");
  });
  it("leaves plain text alone", () => {
    expect(plainLanguage("Rain peaked at 16.4 mm.")).toBe("Rain peaked at 16.4 mm.");
  });
});
