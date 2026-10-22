import type { DataProvenance } from "./provenance";

/** Colour band of a gauge relative to its warning threshold. */
export type GaugeStatus = "ok" | "near" | "over" | "unknown";

export interface GaugeThresholds {
  /** Level at which the gauge turns red. */
  warningCm: number;
  /** Level at which the gauge turns amber. */
  nearCm: number;
  /** What the warning threshold is, e.g. "Warning stage 1" or "MHW (mean high water)". */
  label: string;
}

/** A gauge station as drawn on the map. */
export interface GaugeStation {
  id: string;
  stationName: string;
  river: string;
  /** Agency operating the gauge. */
  operator: string;
  lat: number;
  lon: number;
  /** Latest water level in cm; null when the station reports no current value. */
  levelCm: number | null;
  /** ISO 8601 timestamp of the latest measurement. */
  measuredAt: string | null;
  thresholds: GaugeThresholds | null;
  status: GaugeStatus;
  citationId: string;
  provenance: DataProvenance;
}

/** Result of loading the gauges for one map region. */
export interface RegionGauges {
  regionId: string;
  stations: GaugeStation[];
  provenance: DataProvenance;
  /** ISO 8601 timestamp when the data was fetched from its source. */
  fetchedAt: string;
  /** True when the response came from the short-lived client cache. */
  fromCache: boolean;
  /** Human-readable reason when live data was requested but sample data is shown. */
  fallbackReason?: string;
  /** Attribution required or recommended by the data provider. */
  attribution: string;
}

export interface LevelPoint {
  /** ISO 8601 timestamp. */
  t: string;
  cm: number;
}

/** Forecast band for one time step. Always produced by a model, never measured. */
export interface ForecastPoint {
  t: string;
  lowCm: number;
  midCm: number;
  highCm: number;
}

/** Measured levels behind the gauge drill-down chart. */
export interface GaugeObservations {
  stationId: string;
  /** Hourly levels, oldest first. */
  points: LevelPoint[];
  provenance: DataProvenance;
  citationId: string;
  /** Set when live data was requested but sample data is shown. */
  fallbackReason?: string;
}

/** Forecast band for the drill-down chart. */
export interface GaugeForecast {
  stationId: string;
  points: ForecastPoint[];
  provenance: DataProvenance;
  citationId: string;
}
