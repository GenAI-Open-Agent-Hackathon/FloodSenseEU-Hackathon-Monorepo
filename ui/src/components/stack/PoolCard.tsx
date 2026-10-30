import { useEffect, useState } from "react";
import type { RecordedRun } from "../../api/replay";
import type { LiveRunState } from "../../lib/liveRun";
import { loopsAt, nodeStatesAt, nodesFromLive, traceFrames, type DataKind, type NodeView } from "../../lib/stack";
import { modelDisplay } from "../../lib/techTrace";
import { Empty, StackCard, ms, reducedMotion } from "./StackBits";

const SPEEDS = [1, 2, 4] as const;

function modelText(id: string | null): string {
  if (!id) return "no model call";
  return id
    .split(",")
    .map((m) => (m.trim() === "deterministic" ? "rules" : modelDisplay(m.trim())))
    .join(" + ");
}

export function PoolCard({
  run,
  kind,
  live,
  maxConcurrent,
  inFlight,
}: {
  run: RecordedRun | null;
  kind: DataKind;
  live: LiveRunState | null;
  /** From /platform/status rate_limit; null when the API did not report it. */
  maxConcurrent: number | null;
  inFlight: number | null;
}) {
  const frames = traceFrames(run?.trace);
  const total = frames.length;
  const [played, setPlayed] = useState(total);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const runId = run?.runId ?? null;

  // A newly shown run starts from the top (and plays itself unless motion is reduced).
  useEffect(() => {
    if (reducedMotion() || total === 0) {
      setPlayed(total);
      setPlaying(false);
    } else {
      setPlayed(0);
      setPlaying(true);
    }
  }, [runId, total]);

  useEffect(() => {
    if (!playing) return;
    if (played >= total) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setPlayed((p) => p + 1), 900 / speed);
    return () => clearTimeout(t);
  }, [playing, played, total, speed]);

  const isLive = live !== null;
  const nodes: NodeView[] = isLive ? nodesFromLive(live) : nodeStatesAt(frames, played);
  const loops = isLive ? { revise: live.reviseRounds, repair: live.repairRounds } : loopsAt(frames, played);
  const shownKind: DataKind = isLive ? "live" : run ? kind : "none";
  const done = played >= total;
  const scores = (run?.judgeClaims ?? []).flatMap((j) => (j.score === null ? [] : [j.score]));

  return (
    <StackCard
      id="stk-pool"
      title="Agent pool"
      role="Eight agents work in order. The Skeptic can send the Investigator back; the Judge scores the answer."
      kind={shownKind}
    >
      {isLive && (
        <p className="stk-note" role="status">
          Following run {live.runId} live. {live.announce}
        </p>
      )}
      {!isLive && !run && <Empty>No run with a trace yet. Ask a question to see the agents light up.</Empty>}
      <ol className="stk-steps" aria-label="Agent pipeline">
        {nodes.map((n, i) => (
          <li key={n.id} className={`stk-step stk-step--${n.state}`} aria-current={n.state === "active" ? "step" : undefined}>
            <span className="stk-dot" aria-hidden="true">
              {n.state === "done" ? "✓" : i + 1}
            </span>
            <span className="stk-step-body">
              <strong>{n.label}</strong>
              <span className="stk-note">
                {n.state === "idle" ? "waiting" : n.state === "active" ? "working" : "done"}
                {n.runs > 1 ? ` · ran ${n.runs}×` : ""}
              </span>
              {n.state !== "idle" && (
                <span className="stk-mono">
                  {ms(n.latencyMs)} · {modelText(n.modelId)}
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
      <p className="stk-loops">
        <span className={loops.revise > 0 ? "stk-chip stk-chip--on" : "stk-chip"}>Skeptic ↔ Investigator revise ×{loops.revise}</span>
        <span className={loops.repair > 0 ? "stk-chip stk-chip--on" : "stk-chip"}>Judge repair ×{loops.repair}</span>
        {run?.judgeOverall != null && (done || isLive) && (
          <span className="stk-chip stk-chip--on">
            Judge overall {run.judgeOverall.toFixed(2)}
            {run.judgePasses === false ? " (flagged)" : ""}
          </span>
        )}
        {scores.length > 0 && (done || isLive) && <span className="stk-chip">claim scores {scores.map((s) => s.toFixed(1)).join(", ")}</span>}
      </p>
      {!isLive && total > 0 && (
        <div className="stk-controls" role="group" aria-label="Replay controls">
          <button
            type="button"
            className="stk-btn"
            onClick={() => {
              if (done) setPlayed(0);
              setPlaying((p) => !p || done);
            }}
          >
            {playing ? "Pause" : done ? "Replay" : "Play"}
          </button>
          <label className="stk-scrub">
            <span className="sr-only">Step through the run</span>
            <input
              type="range"
              min={0}
              max={total}
              value={played}
              onChange={(e) => {
                setPlaying(false);
                setPlayed(Number(e.target.value));
              }}
              aria-valuetext={`step ${played} of ${total}`}
            />
          </label>
          <span className="stk-speeds" role="group" aria-label="Speed">
            {SPEEDS.map((s) => (
              <button key={s} type="button" className="stk-btn stk-btn--sm" aria-pressed={speed === s} onClick={() => setSpeed(s)}>
                {s}×
              </button>
            ))}
          </span>
        </div>
      )}
      <p className="stk-note">
        {maxConcurrent !== null
          ? `Pool limit: ${maxConcurrent} full runs at once (${inFlight ?? 0} running now). Further runs wait or get a 429.`
          : "Pool limit not reported (API not reached)."}{" "}
        {run && !isLive ? `Recorded run ${run.runId}${kind === "sample" ? " (bundled sample)" : ""}.` : ""}
      </p>
    </StackCard>
  );
}
