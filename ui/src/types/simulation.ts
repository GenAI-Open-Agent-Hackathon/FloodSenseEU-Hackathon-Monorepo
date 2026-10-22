import type { ApprovalRequest } from "./approval";
import type { Claim } from "./claim";
import type { JudgeScore } from "./judge";
import type { SkepticChallenge } from "./reasoning";

export type SimulationStepId = "threshold" | "investigator" | "skeptic" | "judge" | "queued" | "decision" | "notified";

/** Scripted inputs for one end-to-end alert simulation. All values are sample data. */
export interface SimulationScript {
  id: string;
  gauge: { stationName: string; river: string; fromCm: number; toCm: number; warningCm: number; citationId: string };
  investigatorClaim: Claim;
  skepticChallenge: SkepticChallenge;
  judge: JudgeScore;
  /** The approval request that lands in the insurer queue. */
  request: ApprovalRequest;
}
