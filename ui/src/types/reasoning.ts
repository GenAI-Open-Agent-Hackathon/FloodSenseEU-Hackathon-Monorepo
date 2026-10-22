import type { Claim } from "./claim";
import type { JudgeScore } from "./judge";

export type ChallengeStatus = "resolved" | "conceded" | "open";

/** A Skeptic agent objection to one Investigator claim. */
export interface SkepticChallenge {
  id: string;
  targetClaimId: string;
  challenge: string;
  /** Investigator's response, or the reason the claim was weakened. */
  resolution: string;
  status: ChallengeStatus;
  citationIds: string[];
}

/** Investigator claim -> Skeptic challenge -> Judge score. */
export interface ReasoningChain {
  id: string;
  subject: string;
  investigatorClaims: Claim[];
  skepticChallenges: SkepticChallenge[];
  judge: JudgeScore;
}
