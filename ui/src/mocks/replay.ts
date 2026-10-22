// RECONSTRUCTED SAMPLE data for the time-slider replay. The curves are shaped
// to tell the story of each event but are NOT real measurements.
import type { ReplayScenario, ReplayStation } from "../types";

/** Smooth flood wave: baseline, rising to `peak` at `peakHour`, receding more slowly. */
function wave(hours: number, base: number, peak: number, peakHour: number, riseHours: number, fallHours: number): number[] {
  return Array.from({ length: hours }, (_, h) => {
    const width = h <= peakHour ? riseHours : fallHours;
    const x = (h - peakHour) / width;
    return Math.round(base + (peak - base) * Math.exp(-x * x));
  });
}

function replayStation(s: Omit<ReplayStation, "thresholds"> & { warningCm: number }): ReplayStation {
  const { warningCm, ...rest } = s;
  return { ...rest, thresholds: { warningCm, nearCm: Math.round(warningCm * 0.8), label: "Warning stage 1 (sample value)" } };
}

const DISCLAIMER = "Reconstructed sample, not real measurements.";

const AHR_HOURS = 36;
const VALENCIA_HOURS = 30;

export const replayScenarios: ReplayScenario[] = [
  {
    id: "ahr-2021",
    title: "Ahr valley, 14–15 July 2021",
    regionId: "rlp",
    startAt: "2021-07-14T04:00:00Z",
    hours: AHR_HOURS,
    stations: [
      replayStation({ id: "r-muesch", stationName: "Müsch", river: "Ahr", lat: 50.386, lon: 6.83, warningCm: 220, levelsCm: wave(AHR_HOURS, 70, 420, 13, 6, 9) }),
      replayStation({ id: "r-altenahr", stationName: "Altenahr", river: "Ahr", lat: 50.5167, lon: 6.9886, warningCm: 250, levelsCm: wave(AHR_HOURS, 90, 690, 16, 6, 10) }),
      replayStation({ id: "r-bad-bodendorf", stationName: "Bad Bodendorf", river: "Ahr", lat: 50.556, lon: 7.2156, warningCm: 260, levelsCm: wave(AHR_HOURS, 100, 620, 20, 7, 11) }),
      replayStation({ id: "r-andernach", stationName: "Andernach", river: "Rhine", lat: 50.443, lon: 7.392, warningCm: 550, levelsCm: wave(AHR_HOURS, 420, 560, 26, 9, 12) }),
    ],
    milestones: [
      { hour: 0, label: "Persistent heavy rain over the Eifel (sample timeline)" },
      { hour: 9, label: "Upper Ahr crosses its warning level" },
      { hour: 16, label: "Peak at Altenahr (reconstructed; the real gauge failed)" },
      { hour: 20, label: "Flood wave reaches Bad Bodendorf" },
      { hour: 26, label: "Rhine at Andernach briefly above warning level" },
    ],
    provenance: "reconstructed",
    disclaimer: DISCLAIMER,
    citationId: "cit-replay-ahr-2021",
  },
  {
    id: "valencia-2024",
    title: "Valencia, 29–30 October 2024",
    regionId: "valencia",
    startAt: "2024-10-29T05:00:00Z",
    hours: VALENCIA_HOURS,
    stations: [
      replayStation({ id: "r-poyo-ribaroja", stationName: "Rambla del Poyo (Riba-roja)", river: "Rambla del Poyo", lat: 39.5, lon: -0.55, warningCm: 150, levelsCm: wave(VALENCIA_HOURS, 5, 520, 12, 3, 6) }),
      replayStation({ id: "r-poyo-paiporta", stationName: "Rambla del Poyo (Paiporta)", river: "Rambla del Poyo", lat: 39.428, lon: -0.418, warningCm: 150, levelsCm: wave(VALENCIA_HOURS, 5, 480, 14, 3, 7) }),
      replayStation({ id: "r-turia", stationName: "Turia (Manises)", river: "Turia", lat: 39.49, lon: -0.46, warningCm: 300, levelsCm: wave(VALENCIA_HOURS, 80, 340, 15, 5, 8) }),
      replayStation({ id: "r-magro", stationName: "Magro (Algemesí)", river: "Magro", lat: 39.19, lon: -0.435, warningCm: 260, levelsCm: wave(VALENCIA_HOURS, 60, 410, 17, 5, 9) }),
    ],
    milestones: [
      { hour: 0, label: "Intense rain inland (sample timeline)" },
      { hour: 10, label: "Rambla del Poyo rises within minutes" },
      { hour: 14, label: "Flood wave reaches Paiporta" },
      { hour: 17, label: "Magro peaks at Algemesí" },
    ],
    provenance: "reconstructed",
    disclaimer: DISCLAIMER,
    citationId: "cit-replay-valencia-2024",
  },
];
