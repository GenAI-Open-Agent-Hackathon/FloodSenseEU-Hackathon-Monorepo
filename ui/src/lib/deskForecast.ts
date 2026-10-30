import type { WatchSource } from "./euWatch";
import { sparkSeries, type PointNow } from "./now";

/** The 72 h past + 48 h forecast discharge series for a Valencia hazard_now source; null for any other source (no invented series). */
export function forecastSeriesFor(source: Pick<WatchSource, "id"> | null, valencia: readonly PointNow[]): { values: number[]; split: number | undefined } | null {
  if (!source?.id.startsWith("valencia:")) return null;
  const summary = valencia.find((p) => p.point_id === source.id.slice("valencia:".length));
  if (!summary) return null;
  const series = sparkSeries(summary);
  return series.values.length > 1 ? series : null;
}
