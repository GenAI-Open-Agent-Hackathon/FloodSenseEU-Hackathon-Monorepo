import type { WatchSource } from "./euWatch";
import type { PointNow } from "./now";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function peakText(iso: string): string {
  const d = new Date(iso);
  return `${DAYS[d.getUTCDay()]} ${String(d.getUTCHours()).padStart(2, "0")}:00 UTC`;
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
  return "Water is steady, no rise expected in the next 48 h.";
}
