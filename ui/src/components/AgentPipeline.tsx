import { Fragment, type CSSProperties } from "react";
import type { RecordedRun } from "../api/replay";
import { buildPipeline, formatLatency, type PipelineNode } from "../lib/pipeline";
import { modelLine, type LiveNodeState, type LiveRunState } from "../lib/liveRun";

const STATUS_TEXT: Record<PipelineNode["status"], string> = {
  done: "done",
  flag: "flagged",
  waiting: "waiting",
  skipped: "not run",
};

/** The agent graph for one run: Scope → … → Human approval, with the revise and repair loops. */
export function AgentPipeline({ run, compact = false, title }: { run: RecordedRun; compact?: boolean; title?: string }) {
  const model = buildPipeline(run);
  // The key restarts the reveal when another run is shown.
  return (
    <section className={`agp${compact ? " agp-compact" : ""}`} aria-label={title ?? "Agent pipeline"} key={run.runId}>
      <header className="agp-head">
        <p className="agp-title">{title ?? "Agent pipeline"}</p>
        <p className="agp-meta">
          run {run.runId} · {formatLatency(model.totalLatencyMs)} total
          {model.reviseRounds > 0 && ` · ${model.reviseRounds} revise round${model.reviseRounds === 1 ? "" : "s"}`}
          {model.repairRounds > 0 && ` · ${model.repairRounds} repair round${model.repairRounds === 1 ? "" : "s"}`}
        </p>
      </header>
      <ol className="agp-flow">
        {model.nodes.map((node, i) => (
          <Fragment key={node.id}>
            {i > 0 && (
              <li className="agp-edge" aria-hidden="true" style={{ "--i": i } as CSSProperties}>
                {node.id === "skeptic" && model.reviseRounds > 0 ? (
                  <span className="agp-loop agp-loop-revise" title="Skeptic sent the chain back to the Investigator">
                    ⇄ revise ×{model.reviseRounds}
                  </span>
                ) : (
                  <span className="agp-arrow">→</span>
                )}
              </li>
            )}
            <li className={`agp-node agp-${node.status}`} style={{ "--i": i } as CSSProperties} data-node={node.id}>
              <div className="agp-node-top">
                <span className="agp-name">{node.label}</span>
                <span className={`agp-status agp-status-${node.status}`}>{STATUS_TEXT[node.status]}</span>
              </div>
              <p className="agp-line">
                {formatLatency(node.latencyMs)}
                {node.lane && node.lane !== "none" ? ` · lane ${node.lane}` : ""}
                {node.runs > 1 ? ` · ran ${node.runs}×` : ""}
              </p>
              {node.summary && <p className="agp-summary">{node.summary}</p>}
              {node.badges.length > 0 && (
                <ul className="agp-badges" aria-label={`${node.label} sources`}>
                  {node.badges.map((b) => (
                    <li key={b.text} className={`agp-badge agp-badge-${b.kind}`}>
                      {b.text}
                    </li>
                  ))}
                </ul>
              )}
              {node.id === "judge" && model.repairRounds > 0 && (
                <p className="agp-loop agp-loop-repair" title="Judge flagged claims; Playbook rewrote them to their evidence">
                  ↺ repair ×{model.repairRounds} via Playbook
                </p>
              )}
            </li>
          </Fragment>
        ))}
      </ol>
      {model.board && (
        <p className="agp-board">
          <span className="agp-badge agp-badge-world">World Model</span>{" "}
          {model.board.states.map((s) => (
            <span key={s.id} className={`agp-hyp agp-hyp-${s.state}`}>
              {s.id} {s.state.replace(/_/g, " ")}
            </span>
          ))}
        </p>
      )}
    </section>
  );
}

const LIVE_STATE_TEXT: Record<LiveNodeState, string> = { idle: "queued", running: "running", done: "✓" };

/** The same graph while a run streams: each node lights up on `started` and shows ✓, duration and model on `trace`. */
export function LiveAgentPipeline({ state }: { state: LiveRunState }) {
  return (
    <section className="agp agp-compact agp-live" aria-label="Live agent pipeline">
      <header className="agp-head">
        <p className="agp-title">Agent pipeline · live</p>
        <p className="agp-meta">
          run {state.runId}
          {state.reviseRounds > 0 && ` · ${state.reviseRounds} revise round${state.reviseRounds === 1 ? "" : "s"}`}
          {state.repairRounds > 0 && ` · ${state.repairRounds} repair round${state.repairRounds === 1 ? "" : "s"}`}
        </p>
      </header>
      <ol className="agp-flow">
        {state.nodes.map((node, i) => (
          <Fragment key={node.id}>
            {i > 0 && (
              <li className="agp-edge" aria-hidden="true">
                {node.id === "skeptic" ? (
                  <span className={`agp-arrow${state.reviseRounds > 0 ? " agp-loop agp-loop-revise" : ""}`}>
                    ⇄{state.reviseRounds > 0 ? ` revise ×${state.reviseRounds}` : ""}
                  </span>
                ) : (
                  <span className="agp-arrow">→</span>
                )}
              </li>
            )}
            <li className={`agp-node agp-live-${node.state}`} data-node={node.id} aria-current={node.state === "running" ? "step" : undefined}>
              <div className="agp-node-top">
                <span className="agp-name">{node.label}</span>
                <span className={`agp-status agp-live-status-${node.state}`}>
                  {node.state === "running" && <span className="agp-pulse" aria-hidden="true" />}
                  {LIVE_STATE_TEXT[node.state]}
                </span>
              </div>
              {node.runs > 0 && (
                <p className="agp-line">
                  {formatLatency(node.durationMs)} · {modelLine(node.modelId, node.lane)}
                  {node.runs > 1 ? ` · ran ${node.runs}×` : ""}
                </p>
              )}
              {node.summary && <p className="agp-summary">{node.summary}</p>}
              {node.id === "judge" && state.repairRounds > 0 && (
                <p className="agp-loop agp-loop-repair">↺ repair ×{state.repairRounds} via Playbook</p>
              )}
            </li>
          </Fragment>
        ))}
      </ol>
      {state.loops.length > 0 && (
        <ul className="agp-loops" aria-label="Loops">
          {state.loops.map((l, i) => (
            <li key={`${i}-${l}`}>{l}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
