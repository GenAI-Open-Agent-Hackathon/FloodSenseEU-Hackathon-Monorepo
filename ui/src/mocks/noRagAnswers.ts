// SAMPLE "without retrieval" answers: what the model says from memory alone.
// They deliberately contain unsupported and contradicted claims so the Judge
// comparison is visible. Never shown as advice.
import type { Claim, JudgeScore } from "../types";
import type { AnswerTemplate } from "./answers";

export const judgeFailNoRag: JudgeScore = {
  overall: 0.28,
  groundedness: 0.15,
  citationCoverage: 0,
  skepticResolution: 0.33,
  verdict: "fail",
  rationale: "No claim is backed by a retrieved source. Two claims state numbers with no evidence and one contradicts the current gauge data. The answer must not be shown to users.",
};

interface PlaceFacts {
  name: string;
  river: string;
}

const places: Record<string, PlaceFacts> = {
  "bad-neuenahr-ahrweiler": { name: "Bad Neuenahr-Ahrweiler", river: "Ahr" },
  cologne: { name: "Cologne", river: "Rhine" },
  passau: { name: "Passau", river: "Danube" },
  valencia: { name: "Valencia", river: "Turia" },
};

export function buildNoRagAnswer(locationId: string, question: string): AnswerTemplate {
  const place = places[locationId] ?? { name: "your area", river: "the river" };
  const claims: Claim[] = [
    {
      id: "n1",
      text: `The ${place.river} near ${place.name} is expected to peak at about 4.2 m tomorrow morning.`,
      citationIds: [],
      support: "unsupported",
      judgeNote: "No forecast source; the number is invented.",
    },
    {
      id: "n2",
      text: `Water levels in ${place.name} are currently normal, so no action is needed.`,
      citationIds: [],
      support: "contradicted",
      judgeNote: "Contradicts the current gauge readings and the risk assessment.",
    },
    {
      id: "n3",
      text: "Floods like this typically happen about once every 100 years here.",
      citationIds: [],
      support: "unsupported",
      judgeNote: "Return period stated without any hydrological source.",
    },
  ];
  return { locationId, question, mode: "no-rag", claims, judge: judgeFailNoRag };
}
