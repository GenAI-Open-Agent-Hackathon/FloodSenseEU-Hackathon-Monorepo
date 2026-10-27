import { apiBaseUrl } from "../api/config";
import ahr from "../fixtures/ahr_2021.json";
import { buildFrames, type DisasterEvent, type ReplayPoint, type ReplayReading } from "./disasterReplay";

export interface EventRows {
  rows: ReplayReading[];
  points: ReplayPoint[];
  /** Source line shown under the replay. */
  source: string;
  /** Source badge shown next to "not live". */
  badge: string;
  fromZetaris: boolean;
}

export const AHR_FIXTURE_BADGE = "Bundled modelled data (Open-Meteo, CC BY 4.0), not from Zetaris";

/** VITE_AHR_SOURCE=fixture forces the bundled rows; anything else tries the API first. The one switch. */
export function ahrSourceMode(): "auto" | "fixture" {
  return (import.meta.env.VITE_AHR_SOURCE ?? "").trim().toLowerCase() === "fixture" ? "fixture" : "auto";
}

export function ahrFixture(): EventRows {
  return {
    rows: ahr.hazard_timeline as ReplayReading[],
    points: ahr.points,
    source: ahr._source,
    badge: AHR_FIXTURE_BADGE,
    fromZetaris: false,
  };
}

/** Pure: API rows are usable for the event when they hold its points (by id prefix) inside its window. */
export function usableEventRows(rows: unknown, event: DisasterEvent, prefix: string): ReplayReading[] | null {
  if (!Array.isArray(rows)) return null;
  const mine = rows.filter(
    (r): r is ReplayReading =>
      !!r &&
      typeof r === "object" &&
      typeof (r as ReplayReading).point_id === "string" &&
      (r as ReplayReading).point_id.startsWith(prefix),
  );
  return mine.length && buildFrames(mine, event).length ? mine : null;
}

const AHR_NAMES: Record<string, string> = {
  AHR01: "Altenahr",
  AHR02: "Bad Neuenahr-Ahrweiler",
  AHR03: "Upper Ahr",
};

/**
 * Ahr rows: GET /views/hazard_timeline?event_id=EMSR517 when Zetaris serves AHR points for the window
 * (PR #61 seeds AHR01–AHR04), else the bundled Open-Meteo fixture, labelled as not from Zetaris.
 */
export async function loadAhrRows(event: DisasterEvent, signal?: AbortSignal): Promise<EventRows> {
  if (ahrSourceMode() === "fixture") return ahrFixture();
  try {
    const r = await fetch(`${apiBaseUrl()}/views/hazard_timeline?event_id=${encodeURIComponent(event.eventId)}`, {
      credentials: "omit",
      signal,
    });
    if (r.ok) {
      const rows = usableEventRows(await r.json(), event, "AHR");
      if (rows) {
        const ids = [...new Set(rows.map((x) => x.point_id))].sort();
        return {
          rows,
          points: ids.map((id) => ({ point_id: id, name: AHR_NAMES[id] ?? id })),
          source: `Zetaris hazard_timeline view, event ${event.eventId}, query id ${r.headers.get("x-query-id") ?? "n/a"}. ERA5 hourly rain, GloFAS daily discharge (modelled).`,
          badge: "Zetaris · hazard_timeline",
          fromZetaris: true,
        };
      }
    }
  } catch {
    /* fall back to the fixture */
  }
  return ahrFixture();
}
