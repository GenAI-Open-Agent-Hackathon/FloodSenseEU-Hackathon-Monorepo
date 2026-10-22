import type { JudgeScore } from "./judge";

export type OutboundActionType =
  | "notify-policyholders"
  | "dispatch-loss-adjuster"
  | "flag-underwriting-review";

export type ApprovalStatus = "pending" | "approved" | "rejected";

/** A proposed outbound action. Nothing leaves the system until a human approves. */
export interface ApprovalRequest {
  id: string;
  actionType: OutboundActionType;
  title: string;
  summary: string;
  /** Exact text that would be sent if approved. */
  draftMessage: string;
  targetRegion: string;
  affectedSiteIds: string[];
  /** ISO 8601 timestamp. */
  createdAt: string;
  reasoningChainId: string;
  judge: JudgeScore;
  status: ApprovalStatus;
  reviewerNote?: string;
}

export interface ApprovalDecision {
  requestId: string;
  decision: Exclude<ApprovalStatus, "pending">;
  note: string;
}
