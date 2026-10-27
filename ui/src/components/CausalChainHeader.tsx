import { useEffect, useState } from "react";
import { adoptRunBody, fetchRecordedRun, replayRunId, type RecordedRun } from "../api/replay";
import sampleRun from "../fixtures/run_f16733274f1c.json";
import { AgentPipeline } from "./AgentPipeline";
import { RetrievalPanel } from "./RetrievalPanel";

/** The bundled recorded run (f16733274f1c, Nightshift, one revise and one repair round). Always a replay. */
export function sampleRecordedRun(): RecordedRun | null {
  return adoptRunBody(sampleRun as unknown as Record<string, unknown>, "f16733274f1c");
}

/** Insurer Review header: the agent graph of the reviewed run. VITE_REPLAY_RUN_ID, else the bundled recording. */
export function CausalChainHeader() {
  const [run, setRun] = useState<RecordedRun | null>(() => sampleRecordedRun());
  useEffect(() => {
    const id = replayRunId();
    if (!id) return;
    const controller = new AbortController();
    void fetchRecordedRun(id, undefined, controller.signal).then((r) => {
      if (r && !controller.signal.aborted) setRun(r);
    });
    return () => controller.abort();
  }, []);
  if (!run) return null;
  return (
    <section className="card agp-card" aria-label="Causal chain">
      <p className="section-label">Causal chain</p>
      <p className="note">{run.label}</p>
      <AgentPipeline run={run} title="How the agents reached this answer" />
      <details className="disclosure">
        <summary>Document retrieval and Judge verdicts</summary>
        <RetrievalPanel run={run} />
      </details>
    </section>
  );
}
