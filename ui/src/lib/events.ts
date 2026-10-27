import ahr from "../fixtures/ahr_2021.json";
import type { DischargeDailyRow, ValenciaPoint } from "../types/views";
import type { DisasterEvent } from "./disasterReplay";
import type { PageId } from "./route";

export type EventId = DisasterEvent["eventId"];

/** The event the console opens on: the Valencia views every other page already reads. */
export const DEFAULT_EVENT_ID: EventId = "EMSR773";

export const EVENT_META: Record<EventId, { short: string; region: string }> = {
  EMSR517: { short: "Ahr 2021", region: "Germany · Ahr valley" },
  EMSR773: { short: "Valencia 2024", region: "Spain · Valencia" },
};

/** Header subtitle: "Live" on the Now page, else the selected replay event. */
export function headerSubtitle(page: PageId, eventId: EventId): string {
  if (page === "now") return "Live · Valencia model + Rhine gauges";
  return eventId === "EMSR517" ? "Ahr 2021 replay · EMSR517" : "Valencia replay · EMSR773";
}

/** One map point with real coordinates from the seed rows. */
export interface MapPoint {
  point_id: string;
  name: string;
  /** Short permanent map label, e.g. "Paiporta" or "Dernau". */
  label: string;
  lat: number;
  lon: number;
}

/** Valencia: municipality from the prep CSV (valencia_points). */
export function valenciaMapPoints(points: readonly ValenciaPoint[]): MapPoint[] {
  return points.map((p) => ({
    point_id: p.point_id,
    name: p.name,
    label: p.municipality || p.name.replace(/ centre$/i, ""),
    lat: p.lat,
    lon: p.lon,
  }));
}

/** Ahr: the AHR01–AHR04 points of ingestion/prep/ahr_hazard.py, the same rows as floodsense_seed (migrations 051/052). */
export function ahrMapPoints(): MapPoint[] {
  return ahr.points.map((p) => ({ point_id: p.point_id, name: p.name, label: p.name, lat: p.lat, lon: p.lon }));
}

/** Ahr daily GloFAS discharge, from the same seed rows. */
export function ahrDischarge(): DischargeDailyRow[] {
  return ahr.discharge_daily.map((r) => ({ ...r })) as DischargeDailyRow[];
}

/** Popup / tooltip text for one point on one day. */
export function pointPopupText(point: MapPoint, m3s: number | null, day: string): string {
  const value = m3s === null ? "no discharge row" : `${m3s.toFixed(1)} m³/s`;
  return `${point.point_id} · ${point.name} · ${value} on ${day}`;
}

/** Ahr opens on the GloFAS peak day of the replay window. */
export const AHR_DEFAULT_DATE = "2021-07-14";

/** [[south, west], [north, east]] around the points, or null with none. */
export function boundsOf(points: readonly { lat: number; lon: number }[]): [[number, number], [number, number]] | null {
  if (points.length === 0) return null;
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  return [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ];
}
