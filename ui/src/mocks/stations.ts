// SAMPLE gauge stations for the map. Levels and thresholds are invented for the
// mock and are not real measurements.
import type { GaugeStation, GaugeThresholds } from "../types";
import { gaugeStatus } from "../lib/gaugeStatus";
import { gaugesByLocation } from "./gauges";
import { minutesAgo } from "./time";

function sampleThresholds(warningCm: number): GaugeThresholds {
  return { warningCm, nearCm: Math.round(warningCm * 0.85), label: "Warning stage 1 (sample value)" };
}

interface SampleInput {
  id: string;
  stationName: string;
  river: string;
  operator: string;
  lat: number;
  lon: number;
  levelCm: number;
  warningCm: number;
  citationId: string;
}

function station(input: SampleInput): GaugeStation {
  const thresholds = sampleThresholds(input.warningCm);
  return {
    id: input.id,
    stationName: input.stationName,
    river: input.river,
    operator: input.operator,
    lat: input.lat,
    lon: input.lon,
    levelCm: input.levelCm,
    measuredAt: minutesAgo(12),
    thresholds,
    status: gaugeStatus(input.levelCm, thresholds),
    citationId: input.citationId,
    provenance: "sample",
  };
}

const WSV = "WSV (PEGELONLINE), sample values";

/**
 * Stand-ins for PEGELONLINE federal gauges, shown only when the live feed is
 * unavailable. Keyed by region id.
 */
export const sampleFederalStations: Record<string, GaugeStation[]> = {
  bavaria: [
    station({ id: "s-fed-passau", stationName: "Passau", river: "Danube", operator: WSV, lat: 48.576, lon: 13.459, levelCm: 612, warningCm: 700, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-hofkirchen", stationName: "Hofkirchen", river: "Danube", operator: WSV, lat: 48.677, lon: 13.115, levelCm: 455, warningCm: 500, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-regensburg", stationName: "Regensburg Eiserne Brücke", river: "Danube", operator: WSV, lat: 49.021, lon: 12.1, levelCm: 330, warningCm: 440, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-kelheim", stationName: "Kelheim", river: "Danube", operator: WSV, lat: 48.912, lon: 11.876, levelCm: 298, warningCm: 420, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-wuerzburg", stationName: "Würzburg", river: "Main", operator: WSV, lat: 49.796, lon: 9.926, levelCm: 182, warningCm: 330, citationId: "cit-pegelonline-sample" }),
  ],
  nrw: [
    station({ id: "s-fed-koeln", stationName: "Köln", river: "Rhine", operator: WSV, lat: 50.937, lon: 6.963, levelCm: 421, warningCm: 620, citationId: "cit-pegel-koeln" }),
    station({ id: "s-fed-bonn", stationName: "Bonn", river: "Rhine", operator: WSV, lat: 50.737, lon: 7.104, levelCm: 409, warningCm: 650, citationId: "cit-pegel-bonn" }),
    station({ id: "s-fed-duesseldorf", stationName: "Düsseldorf", river: "Rhine", operator: WSV, lat: 51.227, lon: 6.77, levelCm: 352, warningCm: 710, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-ruhrort", stationName: "Duisburg-Ruhrort", river: "Rhine", operator: WSV, lat: 51.455, lon: 6.729, levelCm: 498, warningCm: 800, citationId: "cit-pegelonline-sample" }),
  ],
  rlp: [
    station({ id: "s-fed-koblenz", stationName: "Koblenz", river: "Rhine", operator: WSV, lat: 50.358, lon: 7.605, levelCm: 286, warningCm: 500, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-andernach", stationName: "Andernach", river: "Rhine", operator: WSV, lat: 50.443, lon: 7.392, levelCm: 341, warningCm: 550, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-trier", stationName: "Trier", river: "Moselle", operator: WSV, lat: 49.757, lon: 6.627, levelCm: 395, warningCm: 600, citationId: "cit-pegelonline-sample" }),
    station({ id: "s-fed-mainz", stationName: "Mainz", river: "Rhine", operator: WSV, lat: 50.004, lon: 8.275, levelCm: 312, warningCm: 550, citationId: "cit-pegelonline-sample" }),
  ],
  valencia: [],
};

const stateOperatorLabel = (operator: string): string => `${operator}, sample values`;

/** Converts the existing per-location gauge mocks into map stations. */
function fromLocationGauges(locationId: string): GaugeStation[] {
  return (gaugesByLocation[locationId] ?? []).map((g) =>
    station({
      id: g.id,
      stationName: g.stationName,
      river: g.river,
      operator: stateOperatorLabel(g.operator),
      lat: g.lat,
      lon: g.lon,
      levelCm: g.levelCm,
      warningCm: g.warningLevelCm,
      citationId: g.citationId,
    }),
  );
}

/**
 * State-portal gauges (HND Bayern, Hochwasserportal NRW, Hochwassermeldedienst
 * RLP) and SAIH Júcar. Always SAMPLE: their data-sharing and licence terms
 * have not been checked yet. Keyed by region id.
 */
export const sampleStateStations: Record<string, GaugeStation[]> = {
  bavaria: [
    // The HND Passau/Danube gauge is omitted: PEGELONLINE already shows Passau.
    ...fromLocationGauges("passau").filter((s) => s.id !== "g-passau-donau"),
    station({ id: "g-isar-muenchen", stationName: "München", river: "Isar", operator: stateOperatorLabel("LfU Bayern (HND)"), lat: 48.122, lon: 11.566, levelCm: 142, warningCm: 300, citationId: "cit-hnd-portal" }),
    station({ id: "g-inn-rosenheim", stationName: "Rosenheim", river: "Inn", operator: stateOperatorLabel("LfU Bayern (HND)"), lat: 47.861, lon: 12.131, levelCm: 268, warningCm: 300, citationId: "cit-hnd-portal" }),
  ],
  nrw: [
    station({ id: "g-erft-bliesheim", stationName: "Bliesheim", river: "Erft", operator: stateOperatorLabel("Hochwasserportal NRW"), lat: 50.787, lon: 6.82, levelCm: 168, warningCm: 190, citationId: "cit-nrw-portal" }),
  ],
  rlp: fromLocationGauges("bad-neuenahr-ahrweiler"),
  valencia: [
    ...fromLocationGauges("valencia"),
    station({ id: "g-poyo-paiporta", stationName: "Rambla del Poyo (Paiporta)", river: "Rambla del Poyo", operator: stateOperatorLabel("CHJ (SAIH Júcar)"), lat: 39.428, lon: -0.418, levelCm: 64, warningCm: 150, citationId: "cit-saih-poyo" }),
    station({ id: "g-magro", stationName: "Magro (Algemesí)", river: "Magro", operator: stateOperatorLabel("CHJ (SAIH Júcar)"), lat: 39.19, lon: -0.435, levelCm: 120, warningCm: 260, citationId: "cit-saih-poyo" }),
  ],
};
