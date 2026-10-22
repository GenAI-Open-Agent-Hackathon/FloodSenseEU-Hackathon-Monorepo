export type JudgeVerdict = "pass" | "needs-review" | "fail";

/** Scores produced by the LLM-as-a-Judge agent before a human sees an answer. */
export interface JudgeScore {
  /** Weighted overall score in the range 0..1. */
  overall: number;
  /** Share of claims supported by their cited evidence, 0..1. */
  groundedness: number;
  /** Share of claims that carry at least one citation, 0..1. */
  citationCoverage: number;
  /** Share of Skeptic challenges that were resolved, 0..1. */
  skepticResolution: number;
  verdict: JudgeVerdict;
  rationale: string;
}
