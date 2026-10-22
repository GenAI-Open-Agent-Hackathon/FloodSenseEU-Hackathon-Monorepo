import type { GaugeReading, Trend } from "../types";
import { minutesAgo } from "./time";

/** Deterministic 24-point hourly series from `start` to `end` with a gentle wobble. */
function series(start: number, end: number, wobble = 3): number[] {
  return Array.from({ length: 24 }, (_, hour) => {
    const progress = hour / 23;
    const eased = progress * progress; // accelerate towards the latest hour
    return Math.round(start + (end - start) * eased + Math.sin(hour * 1.3) * wobble);
  });
}

function gauge(
  base: Omit<GaugeReading, "history24h" | "levelCm" | "measuredAt" | "trend">,
  start: number,
  end: number,
): GaugeReading {
  const history24h = series(start, end);
  const delta = end - start;
  const trend: Trend = delta > 15 ? "rising" : delta < -15 ? "falling" : "steady";
  return { ...base, history24h, levelCm: end, trend, measuredAt: minutesAgo(9) };
}

/** Gauges keyed by location id. Values are MOCK, not real measurements. */
export const gaugesByLocation: Record<string, GaugeReading[]> = {
  "bad-neuenahr-ahrweiler": [
    gauge({ id: "g-altenahr", stationName: "Altenahr", river: "Ahr", operator: "LfU Rheinland-Pfalz", lat: 50.5167, lon: 6.9886, warningLevelCm: 250, citationId: "cit-rlp-altenahr" }, 95, 285),
    gauge({ id: "g-bad-bodendorf", stationName: "Bad Bodendorf", river: "Ahr", operator: "LfU Rheinland-Pfalz", lat: 50.556, lon: 7.2156, warningLevelCm: 260, citationId: "cit-rlp-bodendorf" }, 110, 214),
  ],
  cologne: [
    gauge({ id: "g-koeln", stationName: "Köln", river: "Rhine", operator: "WSV (PEGELONLINE)", lat: 50.9367, lon: 6.9633, warningLevelCm: 620, citationId: "cit-pegel-koeln" }, 388, 421),
    gauge({ id: "g-bonn", stationName: "Bonn", river: "Rhine", operator: "WSV (PEGELONLINE)", lat: 50.737, lon: 7.104, warningLevelCm: 650, citationId: "cit-pegel-bonn" }, 402, 409),
  ],
  passau: [
    gauge({ id: "g-passau-donau", stationName: "Passau", river: "Danube", operator: "LfU Bayern (HND)", lat: 48.574, lon: 13.46, warningLevelCm: 740, citationId: "cit-hnd-passau" }, 560, 705),
    gauge({ id: "g-passau-ingling", stationName: "Passau-Ingling", river: "Inn", operator: "LfU Bayern (HND)", lat: 48.561, lon: 13.443, warningLevelCm: 680, citationId: "cit-hnd-inn" }, 470, 590),
  ],
  valencia: [
    gauge({ id: "g-poyo", stationName: "Rambla del Poyo (Riba-roja)", river: "Rambla del Poyo", operator: "CHJ (SAIH Júcar)", lat: 39.5, lon: -0.55, warningLevelCm: 150, citationId: "cit-saih-poyo" }, 5, 212),
    gauge({ id: "g-turia", stationName: "Turia (Manises)", river: "Turia", operator: "CHJ (SAIH Júcar)", lat: 39.49, lon: -0.46, warningLevelCm: 300, citationId: "cit-saih-poyo" }, 80, 176),
  ],
};
