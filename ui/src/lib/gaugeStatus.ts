import type { GaugeStatus, GaugeThresholds } from "../types";

/** Colour band for a level: red at or above warning, amber at or above near, else green. */
export function gaugeStatus(levelCm: number | null, thresholds: GaugeThresholds | null): GaugeStatus {
  if (levelCm === null || thresholds === null) {
    return "unknown";
  }
  if (levelCm >= thresholds.warningCm) {
    return "over";
  }
  return levelCm >= thresholds.nearCm ? "near" : "ok";
}

export const gaugeStatusLabel: Record<GaugeStatus, string> = {
  ok: "Below warning level",
  near: "Near warning level",
  over: "Above warning level",
  unknown: "No threshold available",
};
