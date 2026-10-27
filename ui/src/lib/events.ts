import ahr from "../fixtures/ahr_2021.json";
import type { DischargeDailyRow, ValenciaPoint } from "../types/views";
import type { DisasterEvent } from "./disasterReplay";
import type { AskContext } from "./askContext";
import type { DeskRoute } from "./route";

export type EventId = DisasterEvent["eventId"];

/** The event the console opens on: Ahr first, as the Replay page always did (Germany-first demo). */
export const DEFAULT_EVENT_ID: EventId = "EMSR517";

export const EVENT_META: Record<EventId, { short: string; region: string }> = {
  EMSR517: { short: "Ahr 2021", region: "Germany · Ahr valley" },
  EMSR773: { short: "Valencia 2024", region: "Spain · Valencia" },
};

/**
 * Header subtitle: "Live" on the Now page, else the event the page actually shows
 * (`shownEventId`, the same rule as the replay strip), so header and strip never disagree.
 */
export function headerSubtitle(route: DeskRoute, eventId: EventId): string {
  if (route.page === "now") return "Live · Valencia model + Rhine gauges";
  return shownEventId(route, eventId) === "EMSR517" ? "Ahr 2021 replay · EMSR517" : "Valencia replay · EMSR773";
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

/** The selected point and replay date of the active event, for the Ask `context`. */
export function activeEventSelection(
  eventId: EventId,
  valencia: { date: string; pointId: string; points: readonly { point_id: string; name: string }[] },
  ahrSel: { date: string; pointId: string },
): { event_id: EventId; replay_date: string; point_id: string; place?: string } {
  if (eventId === "EMSR517") {
    const point = ahrMapPoints().find((p) => p.point_id === ahrSel.pointId);
    return { event_id: eventId, replay_date: ahrSel.date, point_id: ahrSel.pointId, place: point?.name };
  }
  const point = valencia.points.find((p) => p.point_id === valencia.pointId);
  return { event_id: eventId, replay_date: valencia.date, point_id: valencia.pointId, place: point?.name };
}

/** Whether a page shows the selected event, so its Ask `context` may name it. Insurer only; the citizen side routes by question. */
export function pageShowsEvent(route: DeskRoute, eventId: EventId): boolean {
  if (route.role !== "insurer") return false;
  if (route.page === "replay" || route.page === "sites") return true;
  // Portfolio shows an event only when it has an insured book (EMSR773).
  return route.page === "portfolio" && eventId === "EMSR773";
}

/** The event a page shows: the selected one where `pageShowsEvent`, else Valencia (EMSR773). */
export function shownEventId(route: DeskRoute, eventId: EventId): EventId {
  return pageShowsEvent(route, eventId) ? eventId : "EMSR773";
}

/** Pure: the Ask `context` for the page. Event fields only where the page shows that event. */
export function screenContextFor(
  route: DeskRoute,
  eventId: EventId,
  valencia: { date: string; pointId: string; points: readonly { point_id: string; name: string }[] },
  ahrSel: { date: string; pointId: string },
): AskContext {
  if (pageShowsEvent(route, eventId)) {
    return { role: route.role, page: route.page, ...activeEventSelection(eventId, valencia, ahrSel) };
  }
  const point = valencia.points.find((p) => p.point_id === valencia.pointId);
  return { role: route.role, page: route.page, point_id: valencia.pointId, place: point?.name };
}

/**
 * Pure: what the replay strip shows. On a page that shows the selected event it follows that event
 * (Ahr date and point on Ahr). The Simulate playback steps only the Valencia discharge date, so on an
 * Ahr page the strip does not claim Playing/Paused for Ahr; while the Valencia simulation runs it says so
 * and keeps Stop. Pages that show no event keep the Valencia date, point and playback state.
 */
export function replayBarView(
  route: DeskRoute,
  eventId: EventId,
  valencia: { date: string; pointId: string; points: readonly { point_id: string; name: string }[] },
  ahrSel: { date: string; pointId: string },
  playing: boolean,
): { date: string; place: string; playback: "valencia" | "valencia-elsewhere" | "none" } {
  const sel = activeEventSelection(shownEventId(route, eventId), valencia, ahrSel);
  const place = sel.place ? `${sel.point_id} ${sel.place}` : sel.point_id;
  const followsAhr = shownEventId(route, eventId) === "EMSR517";
  const playback = !followsAhr ? "valencia" : playing ? "valencia-elsewhere" : "none";
  return { date: sel.replay_date, place, playback };
}
