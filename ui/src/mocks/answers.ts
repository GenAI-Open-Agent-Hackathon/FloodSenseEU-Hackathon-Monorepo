import type { Answer, Claim, JudgeScore } from "../types";
import { judgePass, judgeReview } from "./judgeScores";

/** A canned answer before cache metadata is attached by the API layer. */
export type AnswerTemplate = Omit<Answer, "id" | "cache" | "retrieval">;

interface Template {
  locationId: string;
  question: string;
  claims: Claim[];
  judge: JudgeScore;
}

export const suggestedQuestions: string[] = [
  "Why is my area at risk right now?",
  "Should I move my car out of the garage?",
  "How does this compare to past floods?",
];

const templates: Template[] = [
  {
    locationId: "bad-neuenahr-ahrweiler",
    question: "Why is my area at risk right now?",
    claims: [
      { id: "q1", text: "Heavy rain upstream is pushing the Ahr above its first warning threshold at Altenahr.", citationIds: ["cit-rlp-altenahr", "cit-openmeteo-ahr"] },
      { id: "q2", text: "Bad Neuenahr-Ahrweiler is downstream, so the rise reaches you with a delay of a few hours.", citationIds: ["cit-rlp-bodendorf"] },
    ],
    judge: judgePass,
  },
  {
    locationId: "bad-neuenahr-ahrweiler",
    question: "How does this compare to past floods?",
    claims: [
      { id: "q1", text: "The current rise is far smaller than in July 2021, but the pattern of a fast upstream rise followed by a delayed downstream peak is similar.", citationIds: ["cit-eval-ahr-2021", "cit-rlp-altenahr"] },
    ],
    judge: judgeReview,
  },
  {
    locationId: "valencia",
    question: "How does this compare to past floods?",
    claims: [
      { id: "q1", text: "As in October 2024, the main danger comes from ramblas that fill within minutes after intense rain.", citationIds: ["cit-eval-valencia-2024", "cit-saih-poyo"] },
    ],
    judge: judgePass,
  },
];

const genericGarageClaim: Claim = {
  id: "q-garage",
  text: "Garages and underpasses are the first places to flood when water levels rise quickly; moving your car early is low-cost and safe.",
  citationIds: [],
};

/**
 * Finds a canned answer for a question. Falls back to the location's risk
 * claims so every answer stays grounded in cited evidence.
 */
export function findAnswerTemplate(locationId: string, question: string, fallbackClaims: Claim[], fallbackJudge: JudgeScore): AnswerTemplate {
  const normalised = question.trim().toLowerCase();
  const match = templates.find((t) => t.locationId === locationId && t.question.toLowerCase() === normalised);
  if (match) {
    return { locationId, question, mode: "rag", claims: match.claims, judge: match.judge };
  }
  const mentionsCar = /car|garage|auto|vehicle/.test(normalised);
  const claims = mentionsCar ? [...fallbackClaims.slice(0, 1), genericGarageClaim] : fallbackClaims.slice(0, 2);
  // General guidance has no citation, so the Judge flags it for human review.
  return { locationId, question, mode: "rag", claims, judge: mentionsCar ? judgeReview : fallbackJudge };
}
