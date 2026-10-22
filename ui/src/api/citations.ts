import { citationsById } from "../mocks/citations";
import type { Citation } from "../types";
import { respond } from "./mockTransport";

/**
 * Citation registry: the sample citations plus citations created at runtime
 * for live data (e.g. one per PEGELONLINE measurement shown).
 * Swap path: replace with GET /citations?ids=… on the FastAPI backend; keep
 * registerCitation for client-side live sources.
 */
const runtimeCitations = new Map<string, Citation>();

/** Adds or replaces a citation produced by a live data adapter. */
export function registerCitation(citation: Citation): void {
  runtimeCitations.set(citation.id, citation);
}

export function getCitations(ids: readonly string[]): Promise<Citation[]> {
  const found = ids
    .map((id) => runtimeCitations.get(id) ?? citationsById.get(id))
    .filter((c): c is Citation => c !== undefined);
  return respond(found, 60);
}

/** Hex SHA-256 prefix of a text, matching the hashes of the sample citations. */
export async function contentHash(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 12);
}
