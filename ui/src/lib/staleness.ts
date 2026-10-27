/**
 * Views served from the API's server-side cache (api/app/views_cache.py).
 * `x-views-cache` is miss | hit | stale; `x-views-age-s` is the age of the copy.
 * A stale copy is the last good reading, kept because the live source failed. It is never presented as live.
 */
export interface ViewCacheInfo {
  view: string;
  cache: "miss" | "hit" | "stale" | null;
  ageS: number | null;
  /** When the copy was read from the live source (ms): now minus its age. */
  goodAt: number | null;
}

export interface StaleView {
  view: string;
  goodAt: number;
  ageS: number;
}

type HeaderSource = { get?: (name: string) => string | null } | undefined | null;

export function cacheInfoOf(view: string, headers: HeaderSource, now = Date.now()): ViewCacheInfo {
  const raw = headers?.get?.("x-views-cache") ?? null;
  const cache = raw === "miss" || raw === "hit" || raw === "stale" ? raw : null;
  const age = Number(headers?.get?.("x-views-age-s") ?? "");
  const ageS = cache && Number.isFinite(age) && age >= 0 ? Math.round(age) : null;
  return { view, cache, ageS, goodAt: ageS === null ? null : now - ageS * 1000 };
}

/** The stale views among the loaded ones. Order is kept. */
export function staleViews(infos: (ViewCacheInfo | null | undefined)[]): StaleView[] {
  const out: StaleView[] = [];
  for (const i of infos) {
    if (i && i.cache === "stale" && i.goodAt !== null && i.ageS !== null) out.push({ view: i.view, goodAt: i.goodAt, ageS: i.ageS });
  }
  return out;
}

function hhmm(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

/** The oldest last-good reading decides the time shown. */
export function staleNote(stale: StaleView[]): string | null {
  if (stale.length === 0) return null;
  const oldest = Math.min(...stale.map((s) => s.goodAt));
  return `Last good reading from ${hhmm(oldest)} UTC (live source temporarily unavailable)`;
}

/** "view eu_watch is 12 min old" for the context strip; several views are listed. */
export function staleStripText(stale: StaleView[]): string | null {
  if (stale.length === 0) return null;
  const names = stale.map((s) => s.view);
  const minutes = Math.max(1, Math.round(Math.max(...stale.map((s) => s.ageS)) / 60));
  const subject = names.length === 1 ? `view ${names[0]} is` : `views ${names.join(", ")} are`;
  return `${subject} ${minutes} min old`;
}
