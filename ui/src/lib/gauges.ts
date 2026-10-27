import { normalizeUtcTimestamp } from "./time";

/** One row of the `gauge_levels` view (contracts/views.yaml). Served by Zetaris, never fetched from PEGELONLINE here. */
export interface GaugeLevelRow {
  station: string;
  water: string;
  ts_utc: string;
  level_cm: number;
  source: string;
}

export type GaugeStatus = "ok" | "near" | "over" | "unknown";
export type Trend = "rising" | "steady" | "falling";

export interface GaugeSummary {
  station: string;
  water: string;
  levelCm: number;
  measuredAt: string;
  trend: Trend | null;
  history: number[];
  source: string;
  /** The view carries no warning level, so every live gauge is "unknown" until one is joined in. */
  status: GaugeStatus;
  warningLevelCm: number | null;
  lat: number | null;
  lon: number | null;
}

export function asGaugeRow(value: unknown): GaugeLevelRow | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const row = value as Record<string, unknown>;
  const station = typeof row.station === "string" ? row.station.trim() : "";
  const water = typeof row.water === "string" ? row.water.trim() : "";
  const source = typeof row.source === "string" ? row.source.trim() : "";
  const level = typeof row.level_cm === "number" && Number.isFinite(row.level_cm) ? row.level_cm : null;
  const ts = typeof row.ts_utc === "string" ? normalizeUtcTimestamp(row.ts_utc) : null;
  if (!station || level === null || !ts) return null;
  return { station, water, ts_utc: ts, level_cm: level, source };
}

function fold(name: string): string {
  return name
    .toUpperCase()
    .replace(/Ä/g, "AE")
    .replace(/Ö/g, "OE")
    .replace(/Ü/g, "UE")
    .replace(/ß/g, "SS")
    .replace(/[^A-Z0-9]+/g, " ")
    .trim();
}

/**
 * Approximate positions of Rhine and Ahr gauges, so the map can place a station the view names.
 * The view has no coordinates. A station missing here is listed but not drawn.
 */
export const STATION_POSITIONS: Record<string, [number, number]> = {
  [fold("Maxau")]: [49.0383, 8.3058],
  [fold("Speyer")]: [49.3238, 8.4489],
  [fold("Mannheim")]: [49.4868, 8.4613],
  [fold("Worms")]: [49.6334, 8.3725],
  [fold("Mainz")]: [50.004, 8.2747],
  [fold("Oestrich")]: [50.0047, 8.0313],
  [fold("Bingen")]: [49.9692, 7.9006],
  [fold("Kaub")]: [50.0853, 7.765],
  [fold("Sankt Goar")]: [50.1525, 7.7146],
  [fold("Koblenz")]: [50.3594, 7.6046],
  [fold("Andernach")]: [50.4399, 7.3912],
  [fold("Oberwinter")]: [50.6152, 7.2117],
  [fold("Bonn")]: [50.7368, 7.1062],
  [fold("Köln")]: [50.9368, 6.9632],
  [fold("Koeln")]: [50.9368, 6.9632],
  [fold("Düsseldorf")]: [51.2257, 6.7703],
  [fold("Ruhrort")]: [51.4554, 6.7289],
  [fold("Duisburg-Ruhrort")]: [51.4554, 6.7289],
  [fold("Wesel")]: [51.6474, 6.6025],
  [fold("Rees")]: [51.7564, 6.3956],
  [fold("Emmerich")]: [51.8296, 6.2453],
  [fold("Altenahr")]: [50.5163, 6.9897],
  [fold("Bad Bodendorf")]: [50.5527, 7.2195],
  [fold("Müsch")]: [50.3865, 6.8285],
};

export function stationPosition(station: string): [number, number] | null {
  return STATION_POSITIONS[fold(station)] ?? null;
}

/** Rhine and Ahr, the area the view covers. */
export const GAUGE_BOUNDS = { south: 49.0, west: 6.1, north: 51.9, east: 8.5 };

const STEADY_CM = 1;

/** Latest reading per station, trend from the previous reading, newest first per station. */
export function summariseGauges(rows: readonly GaugeLevelRow[]): GaugeSummary[] {
  const byStation = new Map<string, GaugeLevelRow[]>();
  for (const row of rows) {
    const key = `${fold(row.station)}|${fold(row.water)}`;
    const list = byStation.get(key);
    if (list) list.push(row);
    else byStation.set(key, [row]);
  }
  const out: GaugeSummary[] = [];
  for (const list of byStation.values()) {
    const sorted = [...list].sort((a, b) => a.ts_utc.localeCompare(b.ts_utc));
    const last = sorted[sorted.length - 1];
    const prev = sorted.length > 1 ? sorted[sorted.length - 2] : null;
    let trend: Trend | null = null;
    if (prev) {
      const delta = last.level_cm - prev.level_cm;
      trend = delta > STEADY_CM ? "rising" : delta < -STEADY_CM ? "falling" : "steady";
    }
    const pos = stationPosition(last.station);
    out.push({
      station: last.station,
      water: last.water,
      levelCm: last.level_cm,
      measuredAt: last.ts_utc,
      trend,
      history: sorted.slice(-48).map((row) => row.level_cm),
      source: last.source,
      status: "unknown",
      warningLevelCm: null,
      lat: pos ? pos[0] : null,
      lon: pos ? pos[1] : null,
    });
  }
  return out.sort((a, b) => a.water.localeCompare(b.water) || a.station.localeCompare(b.station));
}
