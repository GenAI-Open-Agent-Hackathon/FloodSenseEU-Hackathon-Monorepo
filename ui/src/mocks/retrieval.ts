// SAMPLE retrieval traces: which documents the retriever returned for a
// question, with scores and the reason each was used or discarded.
import type { Claim, RetrievalCandidate, RetrievalTrace } from "../types";
import { citationsById } from "./citations";

const TOP_K = 8;
const RELEVANCE_THRESHOLD = 0.55;

/** Candidates that were retrieved but not used, per location. */
const discardedByLocation: Record<string, RetrievalCandidate[]> = {
  "bad-neuenahr-ahrweiler": [
    { id: "d-ahr-news", title: "Three years after the Ahr flood (fictional news article)", publisher: "Example Regional News (fictional)", relevance: 0.77, publishedAt: "2024-07-14", used: false, discardReason: "licence-pointer-only", note: "Copyrighted: only a link and a short quote may be stored, so its text cannot be used as evidence.", citationId: "cit-news-ahr-anniversary" },
    { id: "d-ahr-hazard-2016", title: "Flood hazard map Ahr, 2016 edition (sample document)", publisher: "State environment agency (sample)", relevance: 0.69, publishedAt: "2016-03-01", used: false, discardReason: "outdated", note: "Superseded after July 2021; the hazard zones were redrawn." },
    { id: "d-ahr-drought", title: "Low-water report Rhine tributaries 2022 (sample document)", publisher: "Sample publisher", relevance: 0.41, publishedAt: "2022-09-12", used: false, discardReason: "low-relevance", note: "Below the relevance threshold; about low water, not floods." },
  ],
  cologne: [
    { id: "d-cgn-1993", title: "Rhine flood December 1993, event report (sample document)", publisher: "Sample publisher", relevance: 0.66, publishedAt: "1994-02-01", used: false, discardReason: "outdated", note: "Historic context only; it says nothing about current levels." },
    { id: "d-cgn-mosel", title: "Moselle gauge Trier (sample)", publisher: "PEGELONLINE (sample)", relevance: 0.48, publishedAt: "2026-10-22", used: false, discardReason: "out-of-region", note: "Different river system; below the relevance threshold." },
  ],
  passau: [
    { id: "d-pas-2013-dup", title: "Danube flood June 2013, second copy (sample document)", publisher: "Sample publisher", relevance: 0.72, publishedAt: "2013-06-10", used: false, discardReason: "duplicate", note: "Same content as a document already ranked higher." },
    { id: "d-pas-isar", title: "Isar gauge München (sample)", publisher: "LfU Bayern (HND), sample", relevance: 0.44, publishedAt: "2026-10-22", used: false, discardReason: "low-relevance", note: "Below the relevance threshold for a Passau question." },
  ],
  valencia: [
    { id: "d-vlc-1957", title: "Turia flood 1957, historical summary (sample document)", publisher: "Sample publisher", relevance: 0.64, publishedAt: "2007-10-14", used: false, discardReason: "outdated", note: "The Turia was diverted after 1957; it does not describe today's channels." },
    { id: "d-vlc-news", title: "Ramblas explained (fictional news article)", publisher: "Example Regional News (fictional)", relevance: 0.71, publishedAt: "2024-11-02", used: false, discardReason: "licence-pointer-only", note: "Copyrighted: only a link and a short quote may be stored." },
  ],
};

/**
 * Builds the trace for an answer: every cited source is a "used" candidate,
 * ranked above the discarded ones for that location.
 */
export function buildRetrievalTrace(locationId: string, question: string, claims: readonly Claim[]): RetrievalTrace {
  const citedIds = [...new Set(claims.flatMap((c) => c.citationIds))];
  const used: RetrievalCandidate[] = citedIds.map((citationId, index) => {
    const citation = citationsById.get(citationId);
    return {
      id: `u-${citationId}`,
      title: citation?.title ?? citationId,
      publisher: citation?.publisher ?? "Unknown publisher",
      relevance: Math.round((0.93 - index * 0.04) * 100) / 100,
      publishedAt: citation?.accessedAt ?? "",
      used: true,
      note: "Above the threshold, current and licensed for full use: cited in the answer.",
      citationId,
    };
  });
  const discarded = discardedByLocation[locationId] ?? [];
  return {
    query: question.trim(),
    topK: TOP_K,
    relevanceThreshold: RELEVANCE_THRESHOLD,
    candidates: [...used, ...discarded].sort((a, b) => b.relevance - a.relevance),
  };
}
