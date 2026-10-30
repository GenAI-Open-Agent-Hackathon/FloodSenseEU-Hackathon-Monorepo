import type { WatchSource } from "./euWatch";
import type { PointNow } from "./now";

/** The only forecast places are the Valencia points, so the place's local zone is Europe/Madrid (CET/CEST). */
const PLACE_ZONE = "Europe/Madrid";

function peakText(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-GB", { timeZone: PLACE_ZONE, weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false, timeZoneName: "short" }).formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("weekday")} ${get("hour")}:${get("minute")} ${get("timeZoneName")}`;
}

/**
 * One plain forecast line for a citizen, from the Valencia hazard_now summary only (trend and 48 h forecast max, no numbers shown).
 * Null for any other source or when there is no forecast: nothing is invented.
 */
export function forecastLine(source: Pick<WatchSource, "id"> | null, valencia: readonly PointNow[]): string | null {
  if (!source?.id.startsWith("valencia:")) return null;
  const p = valencia.find((x) => x.point_id === source.id.slice("valencia:".length));
  const now = p?.latest?.discharge_m3s ?? null;
  if (!p || !p.forecastMax || now === null) return null;
  const rise = p.forecastMax.discharge_m3s > now * 1.1 && p.forecastMax.discharge_m3s - now > 0.5;
  if (rise) return `Water is rising and may peak around ${peakText(p.forecastMax.ts_utc)}.`;
  if (p.trend === "down") return "Water is falling, no rise expected in the next 48 h.";
  if (p.trend === "up") return "Water level is up slightly, no big rise expected in the next 48 h.";
  return "Water is steady, no rise expected in the next 48 h.";
}
