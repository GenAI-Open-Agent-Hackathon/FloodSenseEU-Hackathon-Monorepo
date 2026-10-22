/** Why a retrieved document was not used in the answer. */
export type DiscardReason = "outdated" | "low-relevance" | "licence-pointer-only" | "duplicate" | "out-of-region";

/** One document returned by the retriever for a question. */
export interface RetrievalCandidate {
  id: string;
  title: string;
  publisher: string;
  /** Similarity or re-ranker score 0..1. */
  relevance: number;
  /** ISO 8601 date the document was published or last updated. */
  publishedAt: string;
  used: boolean;
  discardReason?: DiscardReason;
  /** Plain-language explanation of the decision. */
  note: string;
  /** Present when the candidate is (or could be) cited. */
  citationId?: string;
}

/** What the retriever did for one answer. */
export interface RetrievalTrace {
  /** Query sent to the retriever after rewriting. */
  query: string;
  /** Number of candidates requested from the vector store. */
  topK: number;
  /** Minimum relevance for a candidate to be considered. */
  relevanceThreshold: number;
  candidates: RetrievalCandidate[];
}
