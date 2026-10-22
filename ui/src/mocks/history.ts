import type { LevelPoint } from "../types";

/** Small deterministic hash so each station gets its own curve shape. */
function seedFrom(id: string): number {
  let hash = 0;
  for (const char of id) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
}

/**
 * SAMPLE hourly history that ends at `endCm`. Starts lower so most sample
 * gauges show a recent rise. Not real measurements.
 */
export function buildSampleHistory(stationId: string, endCm: number, endAt: string, hours = 48): LevelPoint[] {
  const seed = seedFrom(stationId);
  const startCm = endCm * (0.7 + (seed % 20) / 100);
  const phase = (seed % 628) / 100;
  const end = Date.parse(endAt);
  return Array.from({ length: hours }, (_, i) => {
    const progress = i / (hours - 1);
    const level = startCm + (endCm - startCm) * progress * progress + Math.sin(i / 3 + phase) * endCm * 0.01;
    return { t: new Date(end - (hours - 1 - i) * 3_600_000).toISOString(), cm: Math.round(i === hours - 1 ? endCm : level) };
  });
}
