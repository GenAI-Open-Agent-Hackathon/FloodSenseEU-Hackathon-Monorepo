import { crossings, isoOf, type DisasterEvent, type ReplayPoint, type ReplayReading } from "./disasterReplay";

/** One key moment of a replayed flood, as a sentence derived from the replay rows. */
export interface StoryMoment {
  iso: string;
  pointId: string;
  topic: "rain" | "discharge";
  text: string;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "14 Jul, 18:00" (UTC), or "14 Jul" for daily data. */
export function shortWhen(iso: string, daily: boolean): string {
  const d = new Date(iso);
  const day = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
  if (daily) return day;
  return `${day}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

const MAX_MOMENTS = 5;
const MAX_CROSSINGS = 3;

/**
 * Pure: 3-5 key moments, oldest first. The heaviest rain hour (rain is hourly), the first crossings of the
 * event's line (dated by day when discharge is daily), and the peak flow. Nothing is shown that the rows do not hold.
 */
export function storyMoments(
  rows: readonly ReplayReading[],
  points: readonly ReplayPoint[],
  frames: readonly string[],
  event: DisasterEvent,
  daily: boolean,
): StoryMoment[] {
  if (frames.length === 0) return [];
  const inWindow = new Set(frames);
  const name = (pid: string) => points.find((p) => p.point_id === pid)?.name ?? pid;
  const out: StoryMoment[] = [];

  let rain: { r: ReplayReading; iso: string } | null = null;
  let peak: { r: ReplayReading; iso: string } | null = null;
  for (const r of rows) {
    const iso = isoOf(r.ts_utc);
    if (!iso || !inWindow.has(iso)) continue;
    if (r.rain_mm > 0 && (!rain || r.rain_mm > rain.r.rain_mm)) rain = { r, iso };
    if (r.discharge_m3s !== null && (!peak || r.discharge_m3s > (peak.r.discharge_m3s ?? -1))) peak = { r, iso };
  }
  if (rain) {
    out.push({
      iso: rain.iso,
      pointId: rain.r.point_id,
      topic: "rain",
      text: `${shortWhen(rain.iso, false)} — the heaviest rain fell at ${name(rain.r.point_id)}: ${rain.r.rain_mm.toFixed(1)} mm in one hour.`,
    });
  }
  const turned = [...crossings(rows, frames, event.thresholdM3s).entries()].sort((a, b) => a[1].index - b[1].index);
  for (const [pid, c] of turned.slice(0, MAX_CROSSINGS)) {
    out.push({
      iso: c.iso,
      pointId: pid,
      topic: "discharge",
      text: `${shortWhen(c.iso, daily)} — river flow at ${name(pid)} crossed the ${event.thresholdM3s} m³/s alert line${daily ? " (daily value)" : ""}.`,
    });
  }
  if (peak?.r.discharge_m3s != null) {
    const dup = out.some((m) => m.topic === "discharge" && m.pointId === peak!.r.point_id && m.iso === peak!.iso);
    if (!dup) {
      out.push({
        iso: peak.iso,
        pointId: peak.r.point_id,
        topic: "discharge",
        text: `${shortWhen(peak.iso, daily)} — river flow peaked at ${name(peak.r.point_id)}, about ${Math.round(peak.r.discharge_m3s)} m³/s.`,
      });
    }
  }
  // Keep the peak and the rain when trimming: drop the latest crossings first.
  while (out.length > MAX_MOMENTS) {
    const idx = out.map((m, i) => ({ m, i })).filter(({ m }) => m.text.includes("crossed")).pop()?.i ?? out.length - 1;
    out.splice(idx, 1);
  }
  return out.sort((a, b) => a.iso.localeCompare(b.iso));
}
