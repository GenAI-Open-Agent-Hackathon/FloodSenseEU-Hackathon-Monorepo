import { useEffect, useState } from "react";
import { RateLimitError, approvals, decideApproval, startAlertSimulation, submitSimulatedApproval } from "../../api/client";
import { useStore } from "../../hooks/useStore";
import type { ApprovalRequest, SimulationScript, SimulationStepId } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { JudgeScoreBadge } from "../shared/JudgeScoreBadge";

const steps: { id: SimulationStepId; label: string }[] = [
  { id: "threshold", label: "Threshold crossed" },
  { id: "investigator", label: "Investigator" },
  { id: "skeptic", label: "Skeptic" },
  { id: "judge", label: "Judge" },
  { id: "queued", label: "Approval queue" },
  { id: "decision", label: "Human decision" },
  { id: "notified", label: "Notification" },
];

/** Automatic steps advance on a timer; "decision" waits for a person. */
const STEP_MS = 1100;

type RunState =
  | { status: "idle" }
  | { status: "starting" }
  | { status: "running"; script: SimulationScript; step: number; requestId: string | null }
  | { status: "error"; message: string };

interface AlertSimulationProps {
  /** Selects the simulated request in the approval queue card. */
  onShowInQueue: (requestId: string) => void;
}

/** Plays one alert end to end so the human-in-the-loop step is visible. Nothing is sent. */
export function AlertSimulation({ onShowInQueue }: AlertSimulationProps) {
  const [run, setRun] = useState<RunState>({ status: "idle" });
  const queue = useStore(approvals);
  const request: ApprovalRequest | undefined = run.status === "running" && run.requestId ? queue.find((r) => r.id === run.requestId) : undefined;
  const stepId = run.status === "running" ? steps[run.step]?.id : undefined;

  // Advance the automatic steps.
  useEffect(() => {
    if (run.status !== "running" || stepId === "queued" || stepId === "decision" || stepId === "notified") {
      return;
    }
    const timer = window.setTimeout(() => setRun({ ...run, step: run.step + 1 }), STEP_MS);
    return () => window.clearTimeout(timer);
  }, [run, stepId]);

  // Put the request into the queue once the Judge has scored it.
  useEffect(() => {
    if (run.status !== "running" || stepId !== "queued" || run.requestId) {
      return;
    }
    let active = true;
    void submitSimulatedApproval(run.script).then((queued) => {
      if (active) {
        setRun({ ...run, requestId: queued.id, step: run.step + 1 });
        onShowInQueue(queued.id);
      }
    });
    return () => {
      active = false;
    };
  }, [run, stepId, onShowInQueue]);

  // Wait for the human decision, wherever it is made.
  useEffect(() => {
    if (run.status === "running" && stepId === "decision" && request && request.status !== "pending") {
      setRun({ ...run, step: run.step + 1 });
    }
  }, [run, stepId, request]);

  const start = async () => {
    setRun({ status: "starting" });
    try {
      const script = await startAlertSimulation();
      setRun({ status: "running", script, step: 0, requestId: null });
    } catch (error) {
      const message = error instanceof RateLimitError ? error.message : error instanceof Error ? error.message : "Simulation failed.";
      setRun({ status: "error", message });
    }
  };

  const decide = (decision: "approved" | "rejected") => {
    if (request) {
      void decideApproval({ requestId: request.id, decision, note: "Decided from the alert simulation." });
    }
  };

  const finished = run.status === "running" && stepId === "notified";

  return (
    <div className="simulation">
      <div className="simulation__intro">
        <p className="muted small">Plays one sample threshold crossing through the agents into the approval queue. Nothing leaves the browser.</p>
        <button type="button" className="button button--primary" onClick={() => void start()} disabled={run.status === "starting" || (run.status === "running" && !finished)}>
          {finished ? "Run again" : "Simulate alert"}
        </button>
      </div>
      {run.status === "error" && (
        <p className="error error--rate-limit" role="alert">
          {run.message}
        </p>
      )}
      {run.status === "running" && (
        <>
          <ol className="stepper" aria-label="Simulation progress">
            {steps.map((step, i) => (
              <li key={step.id} className={`stepper__step ${i < run.step || finished ? "is-done" : i === run.step ? "is-active" : ""}`} aria-current={i === run.step && !finished ? "step" : undefined}>
                <span className="stepper__dot" aria-hidden="true">
                  {i < run.step || finished ? "✓" : i + 1}
                </span>
                <span className="stepper__label">{step.label}</span>
              </li>
            ))}
          </ol>
          <div className="simulation__detail" aria-live="polite">
            <StepDetail script={run.script} stepIndex={run.step} request={request} onDecide={decide} onShowInQueue={onShowInQueue} />
          </div>
        </>
      )}
    </div>
  );
}

interface StepDetailProps {
  script: SimulationScript;
  stepIndex: number;
  request: ApprovalRequest | undefined;
  onDecide: (decision: "approved" | "rejected") => void;
  onShowInQueue: (id: string) => void;
}

function StepDetail({ script, stepIndex, request, onDecide, onShowInQueue }: StepDetailProps) {
  const { gauge } = script;
  const reached = (id: SimulationStepId) => steps.findIndex((s) => s.id === id) <= stepIndex;
  return (
    <div className="simulation__log">
      <div className="sim-line">
        <span className="chain__role chain__role--threshold">Gauge</span> {gauge.stationName} ({gauge.river}) rose from {gauge.fromCm} to {gauge.toCm} cm, above the {gauge.warningCm} cm warning level.{" "}
        <CitedClaims claims={[{ id: "sim-gauge", text: "", citationIds: [gauge.citationId] }]} variant="prose" showSources={false} />
      </div>
      {reached("investigator") && (
        <div className="sim-line">
          <span className="chain__role chain__role--investigator">Investigator</span>
          <CitedClaims claims={[script.investigatorClaim]} variant="prose" showSources={false} />
        </div>
      )}
      {reached("skeptic") && (
        <div className="sim-line challenge challenge--resolved">
          <span className="chain__role chain__role--skeptic">Skeptic</span> <span className="challenge__text">{script.skepticChallenge.challenge}</span>
          <div className="challenge__resolution">{script.skepticChallenge.resolution}</div>
        </div>
      )}
      {reached("judge") && (
        <div className="sim-line">
          <span className="chain__role chain__role--judge">Judge</span> <JudgeScoreBadge score={script.judge} />
        </div>
      )}
      {reached("decision") && request && (
        <div className="sim-line sim-line--decision">
          <strong>{request.title}</strong>
          {request.status === "pending" ? (
            <>
              <span className="muted small">Waiting for a human. Decide here or in the approval queue.</span>
              <div className="approval__actions">
                <button type="button" className="button button--primary" onClick={() => onDecide("approved")}>
                  Approve
                </button>
                <button type="button" className="button button--danger" onClick={() => onDecide("rejected")}>
                  Reject
                </button>
                <button type="button" className="button" onClick={() => onShowInQueue(request.id)}>
                  Show in queue
                </button>
              </div>
            </>
          ) : (
            <span className={`status status--${request.status}`}>{request.status}</span>
          )}
        </div>
      )}
      {reached("notified") && request && (
        <p className={`status-line status-line--${request.status === "approved" ? "approved" : "rejected"}`}>
          {request.status === "approved" ? "Notification released to the outbox (simulated, nothing was sent). See the bell." : "Action cancelled; the agents were told why. See the bell."}
        </p>
      )}
    </div>
  );
}
