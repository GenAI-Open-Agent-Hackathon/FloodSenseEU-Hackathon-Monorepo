export type Trend = "rising" | "steady" | "falling";

export interface GaugeReading {
  id: string;
  stationName: string;
  river: string;
  /** Agency operating the gauge, e.g. a state flood forecasting centre. */
  operator: string;
  lat: number;
  lon: number;
  levelCm: number;
  warningLevelCm: number;
  trend: Trend;
  /** Hourly water levels in cm for the last 24 hours, oldest first. */
  history24h: number[];
  /** ISO 8601 timestamp of the latest measurement. */
  measuredAt: string;
  citationId: string;
}
