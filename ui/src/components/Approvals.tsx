import { useCallback, useEffect, useId, useState } from "react";
import { useConsole } from "../context/ConsoleContext";
import { fetchApproval, postApproval } from "../api/liveRun";
import { plainLanguage } from "../lib/plain";
import { routeHref } from "../lib/route";
import { getAwaitingRunId, onAwaitingRunId, setAwaitingRunId } from "../lib/lastRun";
import {
  actionChip,
  adoptPlaybook,
  buildApprovalBody,
  cardStatus,
  decisionStatusLine,
  errorDetail,
  sitesLine,
  type ApprovalBody,
  type CardStatus,
  type PlaybookItem,
} from "../lib/hitl";
import "../styles/hitl.css";

interface QueueSource {
  /** null: the packed fixture, decided locally. */
  runId: string | null;
  summary: string;
  items: PlaybookItem[];
  judgeScore: number | null;
  judgePasses: boolean | null;
  status: CardStatus;
  note: string | null;
}

const rec = (v: unknown): Record<string, unknown> | null => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null);

/** Pure: the queue for a GET /runs/{id}/approval body. */
export function queueFromApproval(runId: string, body: Record<string, unknown>): QueueSource {
  const js = rec(body.judge_summary);
  const approval = rec(body.approval);
  return {
    runId,
    summary: typeof body.summary === "string" ? body.summary : "",
    items: adoptPlaybook(body.playbook),
    judgeScore: typeof js?.overall === "number" ? js.overall : null,
    judgePasses: typeof js?.passes === "boolean" ? js.passes : null,
    status: cardStatus(typeof body.status === "string" ? body.status : null, typeof approval?.status === "string" ? approval.status : null),
    note: null,
  };
}

/** The HITL home. One queue item per playbook action; one decision covers the run. Nothing is sent from here. */
export function Approvals() {
  const desk = useConsole();
  const [runId, setRunId] = useState<string | null>(() => getAwaitingRunId());
  const [live, setLive] = useState<QueueSource | null>(null);
  const [loadNote, setLoadNote] = useState<string | null>(null);
  useEffect(() => onAwaitingRunId(setRunId), []);
  useEffect(() => {
    if (!runId) {
      setLive(null);
      return;
    }
    let gone = false;
    void fetchApproval(runId)
      .then(({ status, body }) => {
        if (gone) return;
        if (status === 200 && body) {
          setLive(queueFromApproval(runId, body));
          setLoadNote(null);
        } else {
          setLive(null);
          setLoadNote(
            status === 409
              ? `Run ${runId} is no longer waiting for a decision. Showing the packed example.`
              : `Run ${runId} could not be loaded (${status}${errorDetail(body) ? `: ${errorDetail(body)}` : ""}). Showing the packed example.`,
          );
          if (status === 404 || status === 409) setAwaitingRunId(null);
        }
      })
      .catch(() => {
        if (!gone) setLoadNote("The API could not be reached. Showing the packed example.");
      });
    return () => {
      gone = true;
    };
  }, [runId]);

  const fixtureActions = desk.answer.playbook_actions ?? [];
  const fixture: QueueSource = {
    runId: null,
    summary: desk.answer.question,
    items: fixtureActions.map((a) => ({
      actionId: a.action_id,
      horizonH: null,
      text: plainLanguage(a.detail),
      claimIds: [],
      outbound: a.outbound ?? false,
      released: a.released ?? false,
      actionType: a.action_type ?? null,
      title: a.title,
      targetRegion: a.target_region ?? null,
      affectedSiteCount: a.affected_site_count ?? null,
      draftMessage: a.draft_message ?? null,
    })),
    judgeScore: desk.answer.judge?.overall_score ?? null,
    judgePasses: null,
    status: desk.approval.status,
    note: desk.approval.note ?? null,
  };
  const source = live ?? fixture;

  const decide = useCallback(
    async (body: ApprovalBody): Promise<string | null> => {
      if (!source.runId) {
        const status: CardStatus = body.action === "approve" ? "approved" : body.action === "edit" ? "edited" : "rejected";
        desk.decide(status, body.reviewer_note ?? "");
        return null;
      }
      const result = await postApproval(source.runId, body);
      if (!result.ok) return result.message;
      const approval = rec(result.body?.approval);
      const status = cardStatus(typeof result.body?.status === "string" ? result.body.status : null, typeof approval?.status === "string" ? approval.status : null);
      setLive((cur) =>
        cur
          ? {
              ...cur,
              status: status === "pending" ? (body.action === "reject" ? "rejected" : "approved") : status,
              note: body.reviewer_note ?? null,
              items: body.draft_messages
                ? cur.items.map((i) => (body.draft_messages?.[i.actionId] ? { ...i, draftMessage: body.draft_messages[i.actionId] } : i))
                : cur.items,
            }
          : cur,
      );
      setAwaitingRunId(null);
      return null;
    },
    [desk, source.runId],
  );

  const [selected, setSelected] = useState<string | null>(null);
  const selectedId = selected && source.items.some((i) => i.actionId === selected) ? selected : source.items[0]?.actionId ?? null;

  return (
    <div className="approvals hitl">
      <section className="card" aria-label="Approval queue">
        <p className="section-label">Queue</p>
        <p className="note">
          {source.runId ? `Live run ${source.runId} · one decision covers all its actions.` : "Packed example run · local preview only."}
        </p>
        {loadNote && <p className="note">{loadNote}</p>}
        {source.items.length === 0 ? (
          <p className="note">No playbook action on this run.</p>
        ) : (
          <ul className="approval-list">
            {source.items.map((item) => (
              <ApprovalItem
                key={item.actionId}
                item={item}
                source={source}
                isSelected={item.actionId === selectedId}
                onSelect={() => setSelected(item.actionId)}
                onDecide={decide}
              />
            ))}
          </ul>
        )}
        <p className="note">
          {source.status === "pending" ? `${source.items.length} ${source.items.length === 1 ? "item waits" : "items wait"} for a decision.` : "Nothing is pending."}{" "}
          Nothing is sent: outbound actions are drafts in this demo.
        </p>
        <div className="button-row">
          <button type="button" className="button" onClick={() => desk.openEvidence("discharge")}>
            Open evidence
          </button>
          <a className="button ghost" href={routeHref("insurer", "review")}>
            Read the review chain
          </a>
          {!source.runId && source.status !== "pending" && (
            <button type="button" className="button ghost" onClick={desk.resetApproval}>
              Reset preview
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

function JudgeBadge({ score, passes }: { score: number | null; passes: boolean | null }) {
  if (score === null) return <span className="judge-badge judge-badge--none">Judge · not scored</span>;
  const tone = passes === false || score < 0.7 ? "warn" : "ok";
  return (
    <span className={`judge-badge judge-badge--${tone}`} title="Judge overall score for this run">
      Judge {score.toFixed(2)}
      {passes === null ? "" : passes ? " · passes" : " · does not pass"}
    </span>
  );
}

interface ItemProps {
  item: PlaybookItem;
  source: QueueSource;
  isSelected: boolean;
  onSelect: () => void;
  onDecide: (body: ApprovalBody) => Promise<string | null>;
}

function ApprovalItem({ item, source, isSelected, onSelect, onDecide }: ItemProps) {
  const detailId = useId();
  const [note, setNote] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.draftMessage ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setDraft(item.draftMessage ?? ""), [item.draftMessage]);
  const status = source.status;
  const locked = status !== "pending" || busy;

  const submit = async (action: ApprovalBody["action"], drafts: Record<string, string> = {}) => {
    const built = buildApprovalBody(action, note, drafts, source.items);
    if (!built.ok) {
      setError(built.message);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const message = await onDecide(built.body);
      if (message) setError(message);
      else setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className={`approval approval--${status}${isSelected ? " is-selected" : ""}`}>
      <button type="button" className="approval__summary" onClick={onSelect} aria-expanded={isSelected} aria-controls={detailId}>
        <span className={`chip chip--${item.actionType ?? "action"}`}>{actionChip(item.actionType)}</span>
        <strong>{item.title}</strong>
        <span className="muted small">
          {item.targetRegion ?? "region not stated"} · {sitesLine(item.affectedSiteCount)}
          {item.horizonH !== null ? ` · ${item.horizonH} h` : ""}
        </span>
        <JudgeBadge score={source.judgeScore} passes={source.judgePasses} />
        <span className={`status status--${status}`}>{status}</span>
      </button>

      {isSelected && (
        <div className="approval__detail" id={detailId}>
          <p>{plainLanguage(item.text || source.summary)}</p>
          <p className="eyebrow">Draft message (sent only after approval)</p>
          {item.draftMessage || editing ? (
            editing ? (
              <label className="field">
                <span className="sr-only">Edit draft message for {item.title}</span>
                <textarea value={draft} rows={5} onChange={(e) => setDraft(e.target.value)} disabled={busy} />
              </label>
            ) : (
              <blockquote className="draft">{item.draftMessage}</blockquote>
            )
          ) : (
            <p className="note">{item.outbound ? "No draft was built for this action." : "Internal action: no outbound message."}</p>
          )}
          {status === "pending" ? (
            <>
              <label className="field">
                Reviewer note
                <input
                  type="text"
                  placeholder="Optional. Nothing is sent."
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  disabled={locked}
                />
              </label>
              {error && (
                <p className="error-text" role="alert">
                  {error}
                </p>
              )}
              <div className="approval__actions">
                {editing ? (
                  <>
                    <button
                      type="button"
                      className="button primary"
                      disabled={locked}
                      onClick={() => void submit("edit", { [item.actionId]: draft })}
                      aria-label={`Save edited draft for ${item.title} and approve`}
                    >
                      Save edit
                    </button>
                    <button
                      type="button"
                      className="button"
                      disabled={busy}
                      onClick={() => {
                        setEditing(false);
                        setDraft(item.draftMessage ?? "");
                        setError(null);
                      }}
                    >
                      Cancel edit
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" className="button danger" disabled={locked} onClick={() => void submit("reject")} aria-label={`Reject run with ${item.title}`}>
                      Reject
                    </button>
                    {item.outbound && (
                      <button type="button" className="button" disabled={locked} onClick={() => setEditing(true)} aria-label={`Edit draft for ${item.title}`}>
                        Edit
                      </button>
                    )}
                    <button type="button" className="button primary" disabled={locked} onClick={() => void submit("approve")} aria-label={`Approve run with ${item.title}`}>
                      Approve
                    </button>
                  </>
                )}
              </div>
            </>
          ) : (
            <p className={`status-line status-line--${status === "edited" ? "approved" : status}`} role="status">
              {decisionStatusLine(status)}
              {source.note && <> Note: “{source.note}”</>}
            </p>
          )}
        </div>
      )}
    </li>
  );
}
