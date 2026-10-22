import type { JudgeScore } from "../types";

export const judgePass: JudgeScore = {
  overall: 0.91,
  groundedness: 0.94,
  citationCoverage: 1,
  skepticResolution: 0.83,
  verdict: "pass",
  rationale: "All claims are cited; the numeric values match their Zetaris query results. One Skeptic challenge was resolved by adding the downstream gauge.",
};

export const judgeReview: JudgeScore = {
  overall: 0.72,
  groundedness: 0.78,
  citationCoverage: 0.9,
  skepticResolution: 0.5,
  verdict: "needs-review",
  rationale: "One Skeptic challenge on forecast uncertainty is still open. The human approver should check the precipitation claim before sending.",
};

export const judgeStrong: JudgeScore = {
  overall: 0.95,
  groundedness: 0.97,
  citationCoverage: 1,
  skepticResolution: 1,
  verdict: "pass",
  rationale: "Observed gauge data and forecast agree; every Skeptic challenge was resolved with an additional source.",
};
