import { useState } from "react";
import { formatTime } from "../../lib/format";
import type { ApprovalDecision, ApprovalRequest, OutboundActionType } from "../../types";
import { JudgeScoreBadge } from "../shared/JudgeScoreBadge";

const actionLabel: Record<OutboundActionType, string> = {
  "notify-policyholders": "Notify policyholders",
  "dispatch-loss-adjuster": "Dispatch loss adjuster",
  "flag-underwriting-review": "Underwriting review",
};

interface ApprovalQueueProps {
  requests: readonly ApprovalRequest[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDecide: (decision: ApprovalDecision) => Promise<void>;
}

/** Human-in-the-loop queue. Nothing is sent until a person approves it here. */
export function ApprovalQueue({ requests, selectedId, onSelect, onDecide }: ApprovalQueueProps) {
  return (
    <ul className="approval-list">
      {requests.map((request) => (
        <ApprovalItem
          key={request.id}
          request={request}
          isSelected={request.id === selectedId}
          onSelect={() => onSelect(request.id)}
          onDecide={onDecide}
        />
      ))}
    </ul>
  );
}

interface ApprovalItemProps {
  request: ApprovalRequest;
  isSelected: boolean;
  onSelect: () => void;
  onDecide: (decision: ApprovalDecision) => Promise<void>;
}

function ApprovalItem({ request, isSelected, onSelect, onDecide }: ApprovalItemProps) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const decide = async (decision: ApprovalDecision["decision"]) => {
    setBusy(true);
    try {
      await onDecide({ requestId: request.id, decision, note });
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className={`approval approval--${request.status} ${isSelected ? "is-selected" : ""}`}>
      <button type="button" className="approval__summary" onClick={onSelect} aria-expanded={isSelected}>
        <span className="chip">{actionLabel[request.actionType]}</span>
        <strong>{request.title}</strong>
        <span className="muted small">
          {request.targetRegion} · proposed {formatTime(request.createdAt)}
        </span>
        <JudgeScoreBadge score={request.judge} />
        {request.status !== "pending" && <span className={`status status--${request.status}`}>{request.status}</span>}
      </button>

      {isSelected && (
        <div className="approval__detail">
          <p>{request.summary}</p>
          <p className="eyebrow">Draft message (sent only after approval)</p>
          <blockquote className="draft">{request.draftMessage}</blockquote>
          <JudgeScoreBadge score={request.judge} detailed />
          {request.status === "pending" ? (
            <div className="approval__actions">
              <input
                type="text"
                placeholder="Reviewer note (optional)"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                aria-label="Reviewer note"
              />
              <button type="button" className="button button--danger" disabled={busy} onClick={() => void decide("rejected")}>
                Reject
              </button>
              <button type="button" className="button button--primary" disabled={busy} onClick={() => void decide("approved")}>
                Approve
              </button>
            </div>
          ) : (
            <p className={`status-line status-line--${request.status}`}>
              {request.status === "approved" ? "Approved. In the real system this resumes the LangGraph run and sends the message." : "Rejected. The agent run ends without sending anything."}
              {request.reviewerNote && <> Note: “{request.reviewerNote}”</>}
            </p>
          )}
        </div>
      )}
    </li>
  );
}
