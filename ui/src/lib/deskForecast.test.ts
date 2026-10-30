import { describe, expect, it } from "vitest";
import { forecastLine } from "./deskForecast";
import type { PointNow } from "./now";

const pt = (now: number | null, max: number | null, trend: PointNow["trend"] = "flat"): PointNow =>
  ({
    point_id: "VAL01",
    latest: now === null ? null : { discharge_m3s: now },
    trend,
    forecastMax: max === null ? null : { discharge_m3s: max, ts_utc: "2026-10-30T05:00:00Z" },
  }) as unknown as PointNow;
const val = { id: "valencia:VAL01" };

describe("forecastLine", () => {
  it("rising names the peak time, with no numbers", () => {
    const line = forecastLine(val, [pt(10, 30, "up")]);
    expect(line).toBe("Water is rising and may peak around Fri 06:00 CET.");
    expect(line).not.toMatch(/\d\d\s?m/);
  });
  it("falling and steady", () => {
    expect(forecastLine(val, [pt(10, 10, "down")])).toBe("Water is falling, no rise expected in the next 48 h.");
    expect(forecastLine(val, [pt(10, 10.2, "flat")])).toBe("Water is steady, no rise expected in the next 48 h.");
  });
  it("null when nothing real to say", () => {
    expect(forecastLine({ id: "gauge:X" }, [pt(10, 30)])).toBeNull();
    expect(forecastLine(val, [pt(10, null)])).toBeNull();
    expect(forecastLine(val, [pt(null, 30)])).toBeNull();
    expect(forecastLine(null, [])).toBeNull();
  });
});
