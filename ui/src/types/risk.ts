import type { CacheInfo } from "./cache";
import type { Claim } from "./claim";
import type { JudgeScore } from "./judge";

export type RiskLevel = "low" | "moderate" | "high" | "severe";

export interface RecommendedAction {
  id: string;
  title: string;
  detail: string;
  urgency: "now" | "today" | "prepare";
}

export interface RiskAssessment {
  locationId: string;
  level: RiskLevel;
  /** Composite risk score 0..100. */
  score: number;
  /** Forecast horizon the assessment covers, in hours. */
  horizonHours: number;
  /** Plain-language headline for citizens. */
  headline: string;
  /** Explanation of why the area is at risk, claim by claim. */
  claims: Claim[];
  actions: RecommendedAction[];
  judge: JudgeScore;
  cache: CacheInfo;
}
