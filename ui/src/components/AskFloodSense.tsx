import { useEffect, useId, useRef } from "react";
import { useConsole } from "../context/ConsoleContext";
import { citationMarks, citationsForClaim, numberedCitations } from "../lib/citations";
import { servingLabel, servingQualifier } from "../lib/format";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

/**
 * Gmail-style dock, bottom right. Non-modal: it never covers or pushes the page, and it never opens on a route change.
 * The answer is the fixture already on the desk. There is no question box, because nothing here calls a model.
 */
export function AskFloodSense() {
  const desk = useConsole();
  const { answer, askOpen, closeAsk, evidenceOpen } = desk;
  const panelId = useId();
  const titleId = useId();
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  // A ref, so the drawer opening does not re-run the effect and pull focus around.
  const evidenceOpenRef = useRef(evidenceOpen);
  evidenceOpenRef.current = evidenceOpen;
  // Non-modal: hand focus back to the launcher only if it was still in the panel when it closed.
  const restoreFocusRef = useRef(false);
  const dismiss = () => {
    restoreFocusRef.current = Boolean(panelRef.current?.contains(document.activeElement));
    closeAsk();
  };
  const dismissRef = useRef(dismiss);
  dismissRef.current = dismiss;
  const serving = servingLabel(answer);
  const when = serving.kind === "cached" ? `${serving.text} UTC` : serving.text;
  const badge = serving.kind === "live" ? "Live" : servingQualifier(serving) === "cache" ? "Cached" : "Replay";
  const hasLayerC = answer.citations.some((citation) => citation.layer === "c");

  useEffect(() => {
    if (!askOpen) return;
    closeRef.current?.focus();
    const launcher = launcherRef.current;
    restoreFocusRef.current = false;
    const onKey = (event: KeyboardEvent) => {
      const root = panelRef.current;
      if (!root) return;
      // The Evidence drawer is modal and handles its own Escape.
      if (event.key === "Escape" && !evidenceOpenRef.current) {
        event.preventDefault();
        dismissRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const active = document.activeElement;
      if (!(active instanceof Node) || !root.contains(active)) return;
      const nodes = [...root.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (restoreFocusRef.current) launcher?.focus();
    };
  }, [askOpen, closeAsk]);

  return (
    <div className="ask-dock">
      {askOpen && (
        <section className="ask-panel" id={panelId} role="dialog" aria-modal="false" aria-labelledby={titleId} ref={panelRef}>
          <header className="ask-head">
            <div>
              <h2 id={titleId}>Ask FloodSense</h2>
              <p className={`ask-badge ask-badge-${serving.kind}`}>
                {badge} · {when}
              </p>
            </div>
            <button ref={closeRef} type="button" className="icon-button" aria-label="Close Ask FloodSense" onClick={dismiss}>
              <CloseIcon />
            </button>
          </header>
          <div className="ask-body">
            <p className="note">
              Reviewed answer, {servingQualifier(serving)}, run {serving.runId}. Not live. This panel does not take questions
              or call a model.
            </p>
            <p className="ask-question">{answer.question}</p>
            <ul className="ask-claims">
              {answer.claims.map((claim) => (
                <li key={claim.claim_id}>
                  {claim.text} <span className="cite-marks">{citationMarks(citationsForClaim(answer, claim.claim_id))}</span>
                </li>
              ))}
            </ul>
            <ol className="ask-citations">
              {numberedCitations(answer).map(({ n, citation }) => (
                <li key={citation.citation_id}>
                  [{n}] {citation.title} · {citation.publisher}
                </li>
              ))}
            </ol>
            <details className="disclosure">
              <summary>How I got this</summary>
              <ol className="ask-trace">
                {answer.evidence.map((evidence) => (
                  <li key={evidence.query_id}>
                    <p className="menu-title">{evidence.view}</p>
                    <p className="note">
                      {evidence.query_id} · {evidence.row_count} row{evidence.row_count === 1 ? "" : "s"} · {evidence.executed_at_utc}
                    </p>
                    <pre className="sql">{evidence.sql}</pre>
                  </li>
                ))}
              </ol>
              <p className="note">Fixture SQL, packed with the answer.</p>
              {!hasLayerC && <p className="note">This answer has no layer (c) document citations.</p>}
            </details>
            <div className="button-row">
              <button
                type="button"
                className="button"
                onClick={() => {
                  // Move focus out first, so the drawer records the launcher as its opener.
                  launcherRef.current?.focus();
                  dismiss();
                  desk.openEvidence("discharge");
                }}
              >
                Open evidence
              </button>
            </div>
          </div>
        </section>
      )}
      <button
        ref={launcherRef}
        type="button"
        className="ask-launcher"
        aria-expanded={askOpen}
        aria-controls={askOpen ? panelId : undefined}
        onClick={() => (askOpen ? dismiss() : desk.openAsk())}
      >
        Ask FloodSense
      </button>
    </div>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
