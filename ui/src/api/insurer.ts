/**
 * Insurer view data: portfolio, alerts, reasoning chains and the approval
 * queue (human in the loop). Approvals live in a store so the queue, the KPIs
 * and the alert simulation stay in sync.
 * Swap path: see ui/README.md; the store is filled from GET /approvals and
 * decisions POST to /approvals/{id}/decision (which resumes the LangGraph interrupt).
 */
import { approvalRequests } from "../mocks/approvals";
import { alerts, portfolioSites } from "../mocks/portfolio";
import { reasoningChains } from "../mocks/reasoning";
import { simulationChain } from "../mocks/simulation";
import { createStore, type ReadableStore } from "../lib/createStore";
import type { Alert, ApprovalDecision, ApprovalRequest, PortfolioSite, ReasoningChain } from "../types";
import { notFound, respond } from "./mockTransport";
import { pushNotification, resolveApprovalNotification } from "./notifications";
import { consumeRequest } from "./rateLimiter";

export function listPortfolioSites(): Promise<PortfolioSite[]> {
  return respond(portfolioSites);
}

export function listAlerts(): Promise<Alert[]> {
  return respond(alerts);
}

const allChains: ReasoningChain[] = [...reasoningChains, simulationChain];

export function getReasoningChain(id: string): Promise<ReasoningChain> {
  const chain = allChains.find((c) => c.id === id);
  return chain ? respond(chain) : Promise.reject(notFound("Reasoning chain", id));
}

// --- Approval queue ----------------------------------------------------------

const approvalStore = createStore<ApprovalRequest[]>(approvalRequests);

/** Live view of the approval queue, newest first. */
export const approvals: ReadableStore<ApprovalRequest[]> = approvalStore;

/** Adds a request proposed by the agents. Used by the simulation, not by components. */
export function enqueueApprovalRequest(request: ApprovalRequest): void {
  if (approvalStore.getSnapshot().some((r) => r.id === request.id)) {
    return; // idempotent: a retried submit must not notify twice
  }
  approvalStore.update((list) => [request, ...list.filter((r) => r.id !== request.id)]);
  pushNotification({ kind: "approval-needed", title: "Approval needed", detail: request.title, approvalId: request.id });
}

/** One in-flight decision per request, so a double click cannot spend two agent calls. */
const decisionsInFlight = new Map<string, Promise<ApprovalRequest>>();

/** Records a human decision. In the real system this resumes the LangGraph interrupt. */
export function decideApproval(decision: ApprovalDecision): Promise<ApprovalRequest> {
  const current = decisionsInFlight.get(decision.requestId);
  if (current) {
    return current;
  }
  const pending = applyDecision(decision).finally(() => {
    decisionsInFlight.delete(decision.requestId);
  });
  decisionsInFlight.set(decision.requestId, pending);
  return pending;
}

async function applyDecision(decision: ApprovalDecision): Promise<ApprovalRequest> {
  const request = approvalStore.getSnapshot().find((r) => r.id === decision.requestId);
  if (!request) {
    throw notFound("Approval request", decision.requestId);
  }
  // The queue and the simulation can both offer the same request. The first
  // decision wins; a repeat must not notify again or consume another call.
  if (request.status !== "pending") {
    return request;
  }
  consumeRequest();
  const updated: ApprovalRequest = { ...request, status: decision.decision, reviewerNote: decision.note || undefined };
  const result = await respond(updated, 300);
  approvalStore.update((list) => list.map((r) => (r.id === result.id ? result : r)));
  resolveApprovalNotification(result.id);
  pushNotification({
    kind: "decision",
    title: result.status === "approved" ? "Approved: message released (simulated, nothing sent)" : "Rejected: action cancelled",
    detail: result.title,
    approvalId: result.id,
  });
  return result;
}
