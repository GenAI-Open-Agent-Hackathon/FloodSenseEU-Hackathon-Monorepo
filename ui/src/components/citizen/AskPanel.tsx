import { useEffect, useState, type FormEvent } from "react";
import { RateLimitError, askQuestion, listSuggestedQuestions } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import type { Answer } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { CacheLabel } from "../shared/CacheLabel";
import { JudgeScoreBadge } from "../shared/JudgeScoreBadge";
import { RetrievalTraceView } from "./RetrievalTraceView";

/** The agent pipeline stages, shown while a live answer is being produced. */
const stages = ["Retriever is collecting candidate sources…", "Investigator is building the reasoning chain…", "Skeptic is challenging the claims…", "Judge is scoring the answer…"];

/** "compare" asks twice (with and without retrieval) and shows both side by side. */
type AskMode = "rag" | "no-rag" | "compare";

const modeLabels: Record<AskMode, string> = {
  rag: "With retrieval",
  "no-rag": "Without retrieval",
  compare: "Compare both",
};

type AskState =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "answered"; answers: Answer[] }
  | { status: "error"; message: string; rateLimited: boolean };

export function AskPanel({ locationId, placeName }: { locationId: string; placeName: string }) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<AskMode>("rag");
  const [state, setState] = useState<AskState>({ status: "idle" });
  const [stage, setStage] = useState(0);
  const suggestions = useAsync(listSuggestedQuestions, []);

  useEffect(() => setState({ status: "idle" }), [locationId]);

  useEffect(() => {
    if (state.status !== "pending") {
      return;
    }
    setStage(0);
    const timer = window.setInterval(() => setStage((s) => Math.min(s + 1, stages.length - 1)), 250);
    return () => window.clearInterval(timer);
  }, [state.status]);

  const ask = async (text: string) => {
    if (!text.trim()) {
      return;
    }
    setQuestion(text);
    setState({ status: "pending" });
    try {
      const answers =
        mode === "compare"
          ? await Promise.all([askQuestion(locationId, text, { mode: "rag" }), askQuestion(locationId, text, { mode: "no-rag" })])
          : [await askQuestion(locationId, text, { mode })];
      setState({ status: "answered", answers });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong.";
      setState({ status: "error", message, rateLimited: error instanceof RateLimitError });
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void ask(question);
  };

  return (
    <div className="ask-panel">
      <div className="ask-panel__modes">
        <div className="segmented segmented--small" role="radiogroup" aria-label="Answer mode">
          {(Object.keys(modeLabels) as AskMode[]).map((m) => (
            <button key={m} type="button" role="radio" aria-checked={mode === m} className={`segmented__option ${mode === m ? "is-active" : ""}`} onClick={() => setMode(m)}>
              {modeLabels[m]}
            </button>
          ))}
        </div>
        {mode !== "rag" && <span className="muted small">Comparison only: answers without retrieval are never shown to citizens.{mode === "compare" && " Uses two agent calls."}</span>}
      </div>
      <div className="chips">
        {suggestions.status === "success" &&
          suggestions.data.map((q) => (
            <button key={q} type="button" className="chip chip--button" onClick={() => void ask(q)} disabled={state.status === "pending"}>
              {q}
            </button>
          ))}
      </div>
      <form onSubmit={onSubmit} className="ask-panel__form">
        <input type="text" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={`Ask about ${placeName}…`} aria-label="Your question" />
        <button type="submit" className="button button--primary" disabled={state.status === "pending" || !question.trim()}>
          Ask
        </button>
      </form>

      {state.status === "pending" && (
        <div className="pipeline" aria-live="polite">
          {stages.map((label, i) => (
            <span key={label} className={`pipeline__step ${i < stage ? "is-done" : i === stage ? "is-active" : ""}`}>
              {label}
            </span>
          ))}
        </div>
      )}
      {state.status === "error" && (
        <p className={state.rateLimited ? "error error--rate-limit" : "error"} role="alert">
          {state.message}
          {state.rateLimited && " Cached answers are still available without waiting."}
        </p>
      )}
      {state.status === "answered" && (
        <div className={state.answers.length > 1 ? "answer-compare" : undefined}>
          {state.answers.map((answer) => (
            <AnswerView key={answer.id} answer={answer} />
          ))}
        </div>
      )}
    </div>
  );
}

function AnswerView({ answer }: { answer: Answer }) {
  const [showTrace, setShowTrace] = useState(false);
  return (
    <article className={`answer answer--${answer.mode}`} aria-live="polite">
      <header className="answer__header">
        <span className="answer__mode">{answer.mode === "rag" ? "With retrieval" : "Without retrieval (comparison)"}</span>
        <span className="answer__q">“{answer.question}”</span>
        <div className="answer__meta">
          <CacheLabel cache={answer.cache} />
          <JudgeScoreBadge score={answer.judge} />
        </div>
      </header>
      <CitedClaims claims={answer.claims} variant="prose" />
      {answer.retrieval ? (
        <>
          <button type="button" className="link-button small" onClick={() => setShowTrace((v) => !v)} aria-expanded={showTrace}>
            {showTrace ? "Hide" : "Why these sources?"} ({answer.retrieval.candidates.length} candidates)
          </button>
          {showTrace && <RetrievalTraceView trace={answer.retrieval} claims={answer.claims} />}
        </>
      ) : (
        <p className="notice small">No documents were retrieved, so the Judge cannot verify any sentence.</p>
      )}
      <p className="muted small">Ask the same question again to see the cached label instead of a live answer.</p>
    </article>
  );
}
