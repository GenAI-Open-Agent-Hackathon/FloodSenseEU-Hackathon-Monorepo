import type { ForecastPoint } from "../types";

/**
 * SAMPLE forecast band: continues the last observed trend and widens with lead
 * time. Not a hydrological model.
 */
export function buildForecastBand(lastCm: number, trendCmPerHour: number, startAt: string, hours = 24): ForecastPoint[] {
  const start = Date.parse(startAt);
  return Array.from({ length: hours + 1 }, (_, h) => {
    const damped = trendCmPerHour * h * Math.exp(-h / 18);
    const mid = Math.max(0, lastCm + damped);
    const spread = 4 + h * 1.6;
    return {
      t: new Date(start + h * 3_600_000).toISOString(),
      lowCm: Math.round(Math.max(0, mid - spread)),
      midCm: Math.round(mid),
      highCm: Math.round(mid + spread * 1.3),
    };
  });
}
