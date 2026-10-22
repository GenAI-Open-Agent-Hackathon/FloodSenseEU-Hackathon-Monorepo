/**
 * Citizen view data: locations, risk assessments, nearby gauges and Q&A.
 * Swap path: each function becomes one `fetch` to the FastAPI backend
 * (see ui/README.md, "Swapping mocks for real data").
 */
import { findAnswerTemplate, suggestedQuestions } from "../mocks/answers";
import { gaugesByLocation } from "../mocks/gauges";
import { locations } from "../mocks/locations";
import { buildNoRagAnswer } from "../mocks/noRagAnswers";
import { buildRetrievalTrace } from "../mocks/retrieval";
import { riskByLocation } from "../mocks/risk";
import type { Answer, AnswerMode, GaugeReading, Location, RiskAssessment } from "../types";
import { notFound, respond } from "./mockTransport";
import { consumeRequest } from "./rateLimiter";

const ANSWER_TTL_SECONDS = 15 * 60;

export function listLocations(): Promise<Location[]> {
  return respond(locations);
}

export function getRiskAssessment(locationId: string): Promise<RiskAssessment> {
  const assessment = riskByLocation[locationId];
  return assessment ? respond(assessment) : Promise.reject(notFound("Risk assessment", locationId));
}

/** Gauges listed next to a location (sample values from the state portals). */
export function getGauges(locationId: string): Promise<GaugeReading[]> {
  return respond(gaugesByLocation[locationId] ?? []);
}

export function listSuggestedQuestions(): Promise<string[]> {
  return respond(suggestedQuestions, 0);
}

// --- Answers with cache -----------------------------------------------------

export interface AskOptions {
  /** "rag" (default) grounds the answer in retrieved sources; "no-rag" is for comparison only. */
  mode?: AnswerMode;
}

const answerCache = new Map<string, Answer>();

function cacheKey(locationId: string, question: string, mode: AnswerMode): string {
  return `${mode}|${locationId}|${question.trim().toLowerCase()}`;
}

function isFresh(answer: Answer): boolean {
  return Date.now() - Date.parse(answer.cache.cachedAt) < answer.cache.ttlSeconds * 1000;
}

/**
 * Asks the agent pipeline a question. A fresh cached answer is returned with
 * source "cache" and its original timestamp; it never counts against the
 * rate limit and is never presented as live.
 */
export async function askQuestion(locationId: string, question: string, options: AskOptions = {}): Promise<Answer> {
  const mode = options.mode ?? "rag";
  const key = cacheKey(locationId, question, mode);
  const cached = answerCache.get(key);
  if (cached && isFresh(cached)) {
    return respond({ ...cached, cache: { ...cached.cache, source: "cache" } }, 120);
  }

  consumeRequest();
  const risk = riskByLocation[locationId];
  if (!risk) {
    throw notFound("Location", locationId);
  }
  const template = mode === "rag" ? findAnswerTemplate(locationId, question, risk.claims, risk.judge) : buildNoRagAnswer(locationId, question);
  const answer: Answer = {
    ...template,
    id: `ans-${mode}-${Date.now()}`,
    cache: { source: "live", cachedAt: new Date().toISOString(), ttlSeconds: ANSWER_TTL_SECONDS },
    retrieval: mode === "rag" ? buildRetrievalTrace(locationId, question, template.claims) : undefined,
  };
  answerCache.set(key, answer);
  return respond(answer, 900);
}
