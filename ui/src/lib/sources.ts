import type { ReplayCitation } from "../api/replay";
import type { Citation } from "../types/contract";
import type { MemoryUsed } from "./hitl";

/**
 * Grounded sources per claim. One plain record per numbered badge, from either the contract Citation
 * (Overview) or an adopted run citation (Ask chat). Layer a = data via Zetaris, b = provenance row,
 * c = document passage. Memory is run-level H-MEM recall.
 */
export type SourceKind = "zetaris" | "provenance" | "document" | "memory";

export interface SourceLink {
  href: string;
  label: string;
}

export interface SourceDetail {
  kind: SourceKind;
  /** "Data via Zetaris", "Provenance", "Document", "Approved memory". */
  heading: string;
  title: string;
  /** Short facts: view, query id, publisher, page. */
  facts: string[];
  quote: string | null;
  link: SourceLink | null;
}

export const SOURCE_LEGEND = "Every sentence links to its source: data via Zetaris, documents, or approved memory.";

/** Upstream feeds behind each Zetaris view, from the provenance view rows and docs/legal/sources.md. */
const VIEW_UPSTREAM: { match: RegExp; link: SourceLink }[] = [
  { match: /discharge/i, link: { href: "https://open-meteo.com/en/docs/flood-api", label: "Open-Meteo Flood API (GloFAS)" } },
  {
    match: /hazard_timeline|rain/i,
    link: { href: "https://open-meteo.com/en/docs/historical-weather-api", label: "Open-Meteo historical weather API" },
  },
  { match: /gauge|pegel/i, link: { href: "https://www.pegelonline.wsv.de/", label: "WSV PEGELONLINE" } },
  {
    match: /exposure|footprint|emsr/i,
    link: { href: "https://mapping.emergency.copernicus.eu/activations/EMSR773", label: "Copernicus EMS EMSR773" },
  },
];

/** The upstream source of a Zetaris view, e.g. floodsense.discharge_daily -> Open-Meteo GloFAS. Null when unknown. */
export function upstreamFor(view: string, eventId?: string | null): SourceLink | null {
  const hit = VIEW_UPSTREAM.find((v) => v.match.test(view));
  if (!hit) return null;
  if (/exposure|footprint|emsr/i.test(view) && eventId === "EMSR517") {
    return { href: "https://mapping.emergency.copernicus.eu/activations/EMSR517", label: "Copernicus EMS EMSR517" };
  }
  return hit.link;
}

/** "Seed data" for a floodsense_seed.* view, so a seeded number is never shown as a live feed. */
function seedNote(view: string): string[] {
  return /floodsense_seed\./.test(view) ? ["Seed data (recorded rows)"] : [];
}

function pageFact(page: number | null | undefined, paragraph?: number | null): string[] {
  if (page === null || page === undefined) return [];
  return [paragraph ? `Page ${page}, paragraph ${paragraph}` : `Page ${page}`];
}

function safeLink(url: string | null | undefined, label: string): SourceLink | null {
  return url && /^https?:\/\//i.test(url) ? { href: url, label } : null;
}

/** Pure: a contract citation (Overview, Evidence) as one source record. */
export function sourceFromCitation(c: Citation, eventId?: string | null): SourceDetail {
  if (c.layer === "a") {
    const upstream = upstreamFor(c.title, eventId) ?? safeLink(c.source_url, "Upstream source");
    return {
      kind: "zetaris",
      heading: "Data via Zetaris",
      title: c.title,
      facts: [`View ${c.title}`, ...(c.query_id ? [`Query id ${c.query_id}`] : []), ...seedNote(c.title)],
      quote: c.quote ?? null,
      link: upstream,
    };
  }
  if (c.layer === "b") {
    return {
      kind: "provenance",
      heading: "Provenance",
      title: c.title,
      facts: [c.publisher, c.licence].filter(Boolean),
      quote: c.quote ?? null,
      link: safeLink(c.source_url, c.title),
    };
  }
  return {
    kind: "document",
    heading: "Document",
    title: c.title,
    facts: [c.publisher, ...pageFact(c.locator?.page ?? null, c.locator?.paragraph ?? null)].filter(Boolean),
    quote: c.quote ?? null,
    link: safeLink(c.source_url, c.publisher ? `${c.publisher} source` : "Source"),
  };
}

/** Pure: an adopted run citation (Ask chat) as one source record. */
export function sourceFromRun(c: ReplayCitation, eventId?: string | null): SourceDetail {
  if (c.layer === "a") {
    return {
      kind: "zetaris",
      heading: "Data via Zetaris",
      title: c.title,
      facts: [`View ${c.title}`, ...(c.queryId ? [`Query id ${c.queryId}`] : []), ...seedNote(c.title)],
      quote: c.quote,
      link: upstreamFor(c.title, eventId) ?? safeLink(c.sourceUrl, "Upstream source"),
    };
  }
  if (c.layer === "b") {
    return {
      kind: "provenance",
      heading: "Provenance",
      title: c.title,
      facts: [c.publisher, c.licence].filter((x): x is string => Boolean(x)),
      quote: c.quote,
      link: safeLink(c.sourceUrl, c.title),
    };
  }
  return {
    kind: "document",
    heading: "Document",
    title: c.title,
    facts: [c.publisher ?? "Unknown publisher", ...pageFact(c.page, c.paragraph)],
    quote: c.quote,
    link: safeLink(c.sourceUrl, c.publisher ? `${c.publisher} source` : "Source"),
  };
}

/** "H-MEM · approved run <id>", or "Demo seed" for a seeded memory with no approving run. */
export function memoryLabel(m: Pick<MemoryUsed, "runId">): string {
  return m.runId ? `H-MEM · approved run ${m.runId}` : "H-MEM · Demo seed";
}

export function sourceFromMemory(m: MemoryUsed): SourceDetail {
  return { kind: "memory", heading: "Approved memory", title: memoryLabel(m), facts: [], quote: m.text, link: null };
}
