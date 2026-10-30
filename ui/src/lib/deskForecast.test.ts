import { describe, expect, it } from "vitest";
import { forecastSeriesFor } from "./deskForecast";
import type { PointNow } from "./now";

const row = (v: number | null) => ({ discharge_m3s: v });
const point = { point_id: "VAL01", past: [row(1), row(2)], forecast: [row(3)] } as unknown as PointNow;

describe("forecastSeriesFor", () => {
  it("returns past+forecast for a Valencia source", () => {
    expect(forecastSeriesFor({ id: "valencia:VAL01" }, [point])).toEqual({ values: [1, 2, 3], split: 1 });
  });
  it("returns null for gauges, models and unknown points", () => {
    expect(forecastSeriesFor({ id: "gauge:X" }, [point])).toBeNull();
    expect(forecastSeriesFor({ id: "valencia:NOPE" }, [point])).toBeNull();
    expect(forecastSeriesFor(null, [point])).toBeNull();
  });
});
