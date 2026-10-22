import type { CacheInfo } from "./cache";
import type { Claim } from "./claim";
import type { JudgeScore } from "./judge";
import type { RetrievalTrace } from "./retrieval";

/** "rag" grounds the answer in retrieved documents; "no-rag" asks the model alone. */
export type AnswerMode = "rag" | "no-rag";

/** An agent answer to a free-text question about a location. */
export interface Answer {
  id: string;
  locationId: string;
  question: string;
  mode: AnswerMode;
  claims: Claim[];
  judge: JudgeScore;
  cache: CacheInfo;
  /** Present for "rag" answers: which documents were retrieved and why they were used or discarded. */
  retrieval?: RetrievalTrace;
}
