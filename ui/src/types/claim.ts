/**
 * How well a claim is backed by evidence, as assessed by the Judge.
 * "unsupported" claims have no evidence; "contradicted" claims conflict with it.
 */
export type ClaimSupport = "supported" | "unsupported" | "contradicted";

/** A single factual statement. Rendered with numbered citation markers. */
export interface Claim {
  id: string;
  text: string;
  citationIds: string[];
  /** Judge assessment; omitted means not assessed (treated as supported when cited). */
  support?: ClaimSupport;
  /** Judge note shown next to unsupported or contradicted claims. */
  judgeNote?: string;
}
