/**
 * "Simulate alert" demo: walks one threshold crossing through Investigator,
 * Skeptic and Judge into the approval queue. SAMPLE outputs; nothing is sent.
 * Swap path: POST /simulations/alert on the backend, streaming real step
 * events; the component already renders steps from this typed script.
 */
import { buildSimulationScript } from "../mocks/simulation";
import type { ApprovalRequest, SimulationScript } from "../types";
import { enqueueApprovalRequest } from "./insurer";
import { respond } from "./mockTransport";
import { consumeRequest } from "./rateLimiter";

let runCounter = 0;

/** Starts a simulated pipeline run. Counts as one agent call against the rate limit. */
export function startAlertSimulation(): Promise<SimulationScript> {
  consumeRequest();
  runCounter += 1;
  return respond(buildSimulationScript(runCounter, new Date().toISOString()), 200);
}

/** Puts the simulated request into the insurer approval queue. */
export async function submitSimulatedApproval(script: SimulationScript): Promise<ApprovalRequest> {
  const request = await respond(script.request, 150);
  enqueueApprovalRequest(request);
  return request;
}
