/**
 * Public data-access surface. Components import ONLY from this file, and each
 * function serves one data need behind a typed contract (src/types). Each
 * re-exported module documents its swap path from mock to real backend; see
 * also ui/README.md, "Swapping mocks for real data".
 */
export { getCitations } from "./citations";
export { askQuestion, getGauges, getRiskAssessment, listLocations, listSuggestedQuestions, type AskOptions } from "./citizen";
export { getDefaultRegionId, getGaugeForecast, getGaugeObservations, getRegionGauges, listRegions } from "./gauges";
export { approvals, decideApproval, getReasoningChain, listAlerts, listPortfolioSites } from "./insurer";
export { markNotificationsRead, notifications } from "./notifications";
export { RateLimitError, getRateLimitSnapshot, subscribeRateLimit } from "./rateLimiter";
export { getReplayScenario, listReplayScenarios, type ReplaySummary } from "./replay";
export { getCurrentUser } from "./session";
export { startAlertSimulation, submitSimulatedApproval } from "./simulation";
export { apiBaseUrl, mapTiles, pegelonline as pegelonlineConfig } from "./config";
