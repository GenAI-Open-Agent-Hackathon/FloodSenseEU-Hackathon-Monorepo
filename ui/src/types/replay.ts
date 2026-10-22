import type { DataProvenance } from "./provenance";
import type { GaugeThresholds } from "./station";

export interface ReplayStation {
  id: string;
  stationName: string;
  river: string;
  lat: number;
  lon: number;
  thresholds: GaugeThresholds;
  /** One level per hour, aligned with ReplayScenario.startAt. */
  levelsCm: number[];
}

/** An hour-by-hour replay of a past flood event. */
export interface ReplayScenario {
  id: string;
  title: string;
  regionId: string;
  /** ISO 8601 timestamp of hour 0. */
  startAt: string;
  hours: number;
  stations: ReplayStation[];
  /** Short notes shown at given hours, e.g. "Warning issued". */
  milestones: { hour: number; label: string }[];
  provenance: DataProvenance;
  disclaimer: string;
  citationId: string;
}
