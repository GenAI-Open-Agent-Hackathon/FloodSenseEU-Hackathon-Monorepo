/**
 * Historic event replays for the time slider. RECONSTRUCTED SAMPLE data.
 * Swap path: GET /replays and GET /replays/{id} returning the same shapes.
 */
import { replayScenarios } from "../mocks/replay";
import type { ReplayScenario } from "../types";
import { notFound, respond } from "./mockTransport";

export interface ReplaySummary {
  id: string;
  title: string;
  regionId: string;
}

export function listReplayScenarios(): Promise<ReplaySummary[]> {
  return respond(replayScenarios.map(({ id, title, regionId }) => ({ id, title, regionId })), 50);
}

export function getReplayScenario(id: string): Promise<ReplayScenario> {
  const scenario = replayScenarios.find((s) => s.id === id);
  return scenario ? respond(scenario, 150) : Promise.reject(notFound("Replay", id));
}
