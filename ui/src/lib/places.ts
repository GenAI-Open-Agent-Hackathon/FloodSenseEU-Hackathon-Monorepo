import type { WatchSource } from "./euWatch";
import type { GaugeStatus } from "./gauges";
import type { EventId } from "./events";

/**
 * Citizen places: every live-watch source (PEGELONLINE gauge, GloFAS point, Valencia model point) plus the
 * Valencia and Ahr replay places. Pure; the data comes from the views, nothing here is invented.
 */
export type PlainStatus = "normal" | "watch" | "warning" | "unknown";

export const STATUS_WORD: Record<PlainStatus, string> = {
  normal: "Normal",
  watch: "Watch",
  warning: "Warning",
  unknown: "No reading",
};

/** Worst first. */
export const PLAIN_RANK: Record<PlainStatus, number> = { warning: 0, watch: 1, normal: 2, unknown: 3 };

/** The view band (gauge vs MHW, or the GloFAS model band) as a plain word. */
export function plainStatus(status: GaugeStatus): PlainStatus {
  if (status === "over") return "warning";
  if (status === "near") return "watch";
  if (status === "ok") return "normal";
  return "unknown";
}

/** What the status is measured against, shown next to the word so a model is never read as official. */
export function basisLabel(kind: WatchSource["kind"]): string {
  if (kind === "gauge") return "official gauge threshold (MHW)";
  if (kind === "valencia") return "model · FloodSense demo line, not official";
  return "model, not an official warning";
}

/** One calm sentence a person can read without numbers. */
export function calmSentence(kind: WatchSource["kind"], status: PlainStatus, river: string, name: string): string {
  const where = river ? `The ${river} at ${name}` : name;
  if (status === "unknown") return `We have no current reading for ${name}.`;
  if (kind === "gauge") {
    if (status === "normal") return `${where} is at a normal level, below its mean high water mark.`;
    if (status === "watch") return `${where} is higher than usual and close to its mean high water mark. Keep an eye on official warnings.`;
    return `${where} is above its mean high water mark. Follow your official warning service.`;
  }
  if (status === "normal") return `Our model shows normal river flow for ${where.charAt(0).toLowerCase()}${where.slice(1)} in the coming days.`;
  if (status === "watch")
    return `Our model shows river flow for ${where.charAt(0).toLowerCase()}${where.slice(1)} higher than usual in the coming days. It is a model, not an official warning.`;
  return `Our model shows river flow for ${where.charAt(0).toLowerCase()}${where.slice(1)} well above usual in the coming days. Check your official warning service.`;
}

export interface Place {
  id: string;
  kind: WatchSource["kind"] | "replay";
  name: string;
  river: string;
  /** ISO 3166-1 alpha-2, upper case ("DE", "ES", "FR"). */
  country: string;
  /** Live source behind the place; null for a replay place. */
  source: WatchSource | null;
  /** Replay places only. */
  eventId: EventId | null;
  pointId: string | null;
  /** Extra search words (municipality, country name, point id). */
  keywords: string;
}

const COUNTRY_NAMES: Record<string, string> = {
  DE: "Germany Deutschland",
  ES: "Spain España",
  FR: "France",
  IT: "Italy Italia",
  PL: "Poland Polska",
  AT: "Austria Österreich",
  HU: "Hungary Magyarország",
  BE: "Belgium België Belgique",
  CZ: "Czechia Czech Republic Česko",
};

export function countryName(code: string): string {
  return (COUNTRY_NAMES[code.toUpperCase()] ?? code).split(" ")[0];
}

export function placeFromSource(s: WatchSource): Place {
  return {
    id: s.id,
    kind: s.kind,
    name: s.name,
    river: s.river,
    country: s.country.toUpperCase(),
    source: s,
    eventId: null,
    pointId: null,
    keywords: `${COUNTRY_NAMES[s.country.toUpperCase()] ?? s.country} ${s.id}`,
  };
}

export function replayPlace(
  eventId: EventId,
  point: { point_id: string; name: string; municipality?: string },
): Place {
  const es = eventId === "EMSR773";
  return {
    id: `replay:${point.point_id}`,
    kind: "replay",
    name: point.name,
    river: es ? "" : "Ahr",
    country: es ? "ES" : "DE",
    source: null,
    eventId,
    pointId: point.point_id,
    keywords: `${point.municipality ?? ""} ${point.point_id} ${es ? "Valencia 2024 DANA" : "Ahr 2021"} ${COUNTRY_NAMES[es ? "ES" : "DE"]}`,
  };
}

/** Live sources first, then the replay places. */
export function buildPlaces(
  sources: readonly WatchSource[],
  valencia: readonly { point_id: string; name: string; municipality?: string }[],
  ahr: readonly { point_id: string; name: string }[],
): Place[] {
  return [
    ...sources.map(placeFromSource),
    ...valencia.map((p) => replayPlace("EMSR773", p)),
    ...ahr.map((p) => replayPlace("EMSR517", p)),
  ];
}

/** Case- and accent-insensitive. */
export function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/ß/g, "ss")
    .toLowerCase();
}

/** Every word of the query must match the place's name, river, country or keywords. Empty query: all places. */
export function searchPlaces(places: readonly Place[], query: string): Place[] {
  const words = fold(query).split(/\s+/).filter(Boolean);
  if (words.length === 0) return [...places];
  return places.filter((p) => {
    const hay = fold(`${p.name} ${p.river} ${p.country} ${p.keywords}`);
    return words.every((w) => hay.includes(w));
  });
}

export function plainOf(s: WatchSource): PlainStatus {
  return plainStatus(s.status);
}

/** Worst first, then by ratio (highest first), then name. */
export function worstFirst(list: readonly WatchSource[]): WatchSource[] {
  return [...list].sort(
    (a, b) =>
      PLAIN_RANK[plainOf(a)] - PLAIN_RANK[plainOf(b)] || (b.ratio ?? -1) - (a.ratio ?? -1) || a.name.localeCompare(b.name),
  );
}

/** The replay event of a place id ("replay:VAL01" -> EMSR773, "replay:AHR01" -> EMSR517), else null. */
export function replayEventOfPlace(placeId: string | null): EventId | null {
  if (!placeId?.startsWith("replay:")) return null;
  const point = placeId.slice("replay:".length);
  if (/^VAL\d+$/i.test(point)) return "EMSR773";
  if (/^AHR\d+$/i.test(point)) return "EMSR517";
  return null;
}

/** The Ask question for a chosen place. */
export function questionForPlace(place: Place): string {
  if (place.source) return place.source.question;
  return place.eventId === "EMSR517"
    ? `What happened at ${place.name} in the Ahr flood of July 2021?`
    : `What happened at ${place.name} in the Valencia flood of October 2024?`;
}

/** Counts per plain status, for "anywhere in our watch". */
export function statusCounts(list: readonly WatchSource[]): Record<PlainStatus, number> {
  const out: Record<PlainStatus, number> = { normal: 0, watch: 0, warning: 0, unknown: 0 };
  for (const s of list) out[plainOf(s)] += 1;
  return out;
}

