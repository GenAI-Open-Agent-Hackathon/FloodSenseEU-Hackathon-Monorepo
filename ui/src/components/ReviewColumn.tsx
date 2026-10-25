import { useEffect, useState } from "react";
import { causalChain, skepticVerdicts } from "../fixtures/console";
import { useConsole } from "../context/ConsoleContext";
import type { ApprovalStatus, Grounding } from "../types/contract";
import type { SkepticOutcome } from "../fixtures/console";

export function ReviewColumn() {
  const desk = useConsole();
  const [tab, setTab] = useState<"chain" | "skeptic" | "judge" | "approval">("chain");
  const [note, setNote] = useState(desk.approval.note ?? "");
  const [noteError, setNoteError] = useState("");
  const judge = desk.answer.judge;
  const action = desk.answer.playbook_actions?.[0];
  const locked = desk.approval.status !== "pending";

  useEffect(() => {
    setNote(desk.approval.note ?? "");
    setNoteError("");
  }, [desk.approval]);

  function commit(status: ApprovalStatus) {
    if ((status === "rejected" || status === "edited") && note.trim().length === 0) {
      setNoteError(status === "rejected" ? "A note is required to reject." : "Add a note to record the edit.");
      return;
    }
    setNoteError("");
    desk.decide(status, note.trim());
  }

  return (
    <section className="card review" aria-label="Review">
      <div className="card-head">
        <div>
          <p className="section-label">Reviewed answer</p>
          <h2>{desk.answer.question}</h2>
        </div>
      </div>
      <p className="note">
        Skeptic notes and Judge scores are fixtures for this screen. They are not a Nightshift call, and they do not
        choose a model lane. The human still decides. Nothing here is sent.
      </p>
      <div className="tablist" role="tablist" aria-label="Review sections">
        {(
          [
            ["chain", "Causal chain"],
            ["skeptic", "Skeptic"],
            ["judge", "Judge"],
            ["approval", desk.approval.status === "pending" ? "Approval" : `Approval · ${desk.approval.status}`],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            className={tab === id ? "tab active" : "tab"}
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
        <button type="button" className="tab tab-link" onClick={() => desk.openEvidence("discharge")}>
          Evidence
        </button>
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="tab-panel">
        {tab === "chain" && (
          <ol className="chain">
            {causalChain.map((link) => {
              const claim = desk.answer.claims.find((item) => item.claim_id === link.claim_id);
              const verdict = skepticVerdicts.find((item) => item.claim_id === link.claim_id);
              const score = judge?.claims.find((item) => item.claim_id === link.claim_id);
              return (
                <li key={link.id} className="step">
                  <p className="step-label">{link.label}</p>
                  <h3>{link.title}</h3>
                  <p>{claim?.text}</p>
                  <p className="note">{link.note}</p>
                  <div className="badge-row">
                    {verdict && <OutcomeBadge outcome={verdict.outcome} />}
                    {score && <GroundingBadge grounding={score.grounding} score={score.score} />}
                  </div>
                </li>
              );
            })}
          </ol>
        )}
        {tab === "skeptic" && (
          <ul className="stack">
            {skepticVerdicts.map((verdict) => {
              const claim = desk.answer.claims.find((item) => item.claim_id === verdict.claim_id);
              return (
                <li key={verdict.claim_id} className="step">
                  <OutcomeBadge outcome={verdict.outcome} />
                  <h3>{claim?.text}</h3>
                  <p>{verdict.counter_check}</p>
                </li>
              );
            })}
          </ul>
        )}
        {tab === "judge" && judge && (
          <div className="stack">
            <div className="score-block">
              <p className="section-label">overall_score</p>
              <p className="figure">{judge.overall_score.toFixed(2)}</p>
              <div className="meter" aria-hidden="true">
                <span style={{ width: `${Math.max(0, Math.min(1, judge.overall_score)) * 100}%` }} />
              </div>
              <p className="note">
                model_id on each claim is the contract’s deep lane, copied so the fixture matches the schema. This
                screen did not call it.
              </p>
            </div>
            {judge.claims.map((claim) => {
              const text = desk.answer.claims.find((item) => item.claim_id === claim.claim_id)?.text;
              return (
                <article key={claim.claim_id} className="step">
                  <div className="badge-row">
                    <GroundingBadge grounding={claim.grounding} score={claim.score} />
                    <span className="badge">{claim.numbers_match ? "numbers_match" : "numbers differ"}</span>
                    <span className="badge">
                      {claim.citation_faithful ? "citation_faithful" : "citation not faithful"}
                    </span>
                  </div>
                  <h3>{text}</h3>
                  <p>{claim.rationale}</p>
                  <p className="note">{claim.model_id}</p>
                </article>
              );
            })}
          </div>
        )}
        {tab === "judge" && !judge && <p className="note">This answer has no judge block.</p>}
        {tab === "approval" && (
          <div className="stack">
            {action ? (
              <>
                <h3>{action.title}</h3>
                <p>{action.detail}</p>
                <p className="note">action_id {action.action_id}</p>
              </>
            ) : (
              <p className="note">No playbook action on this answer.</p>
            )}
            <p className="status-line">
              Status <strong>{desk.approval.status}</strong>
              {judge ? ` · judge overall ${judge.overall_score.toFixed(2)}` : ""}
            </p>
            <label className="field">
              Review note
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows={3}
                disabled={locked}
                placeholder="Required for edit or reject. Nothing is sent."
              />
            </label>
            {noteError && (
              <p className="error-text" role="alert">
                {noteError}
              </p>
            )}
            <div className="button-row">
              <button type="button" className="button primary" disabled={locked} onClick={() => commit("approved")}>
                Approve
              </button>
              <button type="button" className="button" disabled={locked} onClick={() => commit("edited")}>
                Edit
              </button>
              <button type="button" className="button danger" disabled={locked} onClick={() => commit("rejected")}>
                Reject
              </button>
              {locked && (
                <button type="button" className="button ghost" onClick={desk.resetApproval}>
                  Reset preview
                </button>
              )}
            </div>
            <p className="note">Local preview only. Approving does not send an outbound action and does not change the Judge scores.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function OutcomeBadge({ outcome }: { outcome: SkepticOutcome }) {
  return <span className={`badge badge-${outcome}`}>{outcome}</span>;
}

function GroundingBadge({ grounding, score }: { grounding: Grounding; score: number }) {
  return (
    <span className={`badge badge-${grounding}`}>
      {grounding} {score.toFixed(2)}
    </span>
  );
}
