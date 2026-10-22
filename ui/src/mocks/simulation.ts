// SAMPLE script for the "Simulate alert" demo. It replays the full pipeline
// with canned outputs; nothing is sent to anyone.
import type { JudgeScore, ReasoningChain, SimulationScript } from "../types";

const judgeSimulation: JudgeScore = {
  overall: 0.89,
  groundedness: 0.93,
  citationCoverage: 1,
  skepticResolution: 0.8,
  verdict: "pass",
  rationale: "The threshold crossing is backed by the gauge reading and the Skeptic's tributary question was answered with the Inn gauge. Safe to put in front of a human approver.",
};

export const simulationChain: ReasoningChain = {
  id: "rc-sim-passau",
  subject: "Simulated: warn Passau Altstadt policyholders",
  investigatorClaims: [
    { id: "i1", text: "The Danube at Passau has crossed its warning level (740 cm) and is still rising.", citationIds: ["cit-hnd-passau"] },
    { id: "i2", text: "Rain over the Inn catchment keeps feeding the rise for the next 24 hours.", citationIds: ["cit-openmeteo-passau"] },
    { id: "i3", text: "103 policies at two sites lie in the Altstadt and Innstadt flood zone.", citationIds: ["cit-portfolio"] },
  ],
  skepticChallenges: [
    {
      id: "sk1",
      targetClaimId: "i1",
      challenge: "Could the rise come from the Inn backing up rather than the Danube itself? Then the warning area would differ.",
      resolution: "Resolved: the Inn gauge at Passau-Ingling is rising too, and both rivers affect the same two sites.",
      status: "resolved",
      citationIds: ["cit-hnd-inn"],
    },
  ],
  judge: judgeSimulation,
};

/** Builds a fresh script; `runId` keeps request ids unique across repeated runs. */
export function buildSimulationScript(runId: number, createdAt: string): SimulationScript {
  const [claim] = simulationChain.investigatorClaims;
  const [challenge] = simulationChain.skepticChallenges;
  if (!claim || !challenge) {
    throw new Error("Simulation chain is incomplete");
  }
  return {
    id: `sim-${runId}`,
    gauge: { stationName: "Passau", river: "Danube", fromCm: 712, toCm: 748, warningCm: 740, citationId: "cit-hnd-passau" },
    investigatorClaim: claim,
    skepticChallenge: challenge,
    judge: judgeSimulation,
    request: {
      id: `ap-sim-${runId}`,
      actionType: "notify-policyholders",
      title: "Simulated: warn 103 Passau policyholders",
      summary: "Danube above warning level at Passau. Warn Altstadt and Innstadt policyholders to protect ground floors tonight.",
      draftMessage: "FloodSense (simulation, not sent): The Danube in Passau is above its warning level and still rising. Move valuables out of basements and ground floors and follow official warnings.",
      targetRegion: "Bavaria",
      affectedSiteIds: ["s-07", "s-08"],
      createdAt,
      reasoningChainId: simulationChain.id,
      judge: judgeSimulation,
      status: "pending",
    },
  };
}
