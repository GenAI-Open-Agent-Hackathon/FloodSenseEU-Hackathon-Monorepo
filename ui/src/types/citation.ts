/**
 * Citation contracts. Every claim shown to a user must point to at least one
 * Citation. Layer 1 is the Zetaris query behind a number, layer 2 is the
 * source URL, layer 3 is the exact location inside the source document.
 */

/** Where inside a source document the quoted text was found. */
export interface SourceLocator {
  section?: string;
  page?: number;
  paragraph?: number;
  /** Line range inside the paragraph, e.g. "3-5". */
  lines?: string;
}

/** The federated Zetaris query that produced a numeric value. */
export interface ZetarisProvenance {
  /** Fully qualified dataset name as registered in Zetaris. */
  dataset: string;
  /** The SQL that was run, exactly as sent. */
  query: string;
  rowCount: number;
  /** ISO 8601 timestamp of query execution. */
  executedAt: string;
}

/**
 * Open-licensed sources may be stored in full. Copyrighted or paywalled
 * sources are fetched on demand; only the pointer and a short quote are kept.
 */
export type StoragePolicy = "full-text" | "pointer-and-quote";

export interface Citation {
  id: string;
  url: string;
  title: string;
  publisher: string;
  /** ISO 8601 date the source was accessed. */
  accessedAt: string;
  locator: SourceLocator;
  /** Short verbatim quote (1-2 sentences) supporting the claim. */
  quote: string;
  /** True while the quote is placeholder text written for the mock. */
  quoteIsSample: boolean;
  /** SHA-256 of the quote text, shortened to 12 hex characters for display. */
  contentHash: string;
  license: string;
  storage: StoragePolicy;
  /** Present when the cited value came out of a Zetaris federated query. */
  zetaris?: ZetarisProvenance;
}
