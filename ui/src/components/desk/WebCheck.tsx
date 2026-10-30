import "../../styles/sponsors.css";
import type { StackData } from "../../hooks/useStackData";
import { WEB_NOT_WARNING, webCheckView, webContextOf } from "../../lib/sponsors";
import { SafeLink } from "../SafeLink";
import { DataBadge } from "../stack/StackBits";
import { DeskCard } from "./DeskPage";

/**
 * Evidence slot: the Tavily web check of the run shown (Skeptic verdict in plain words, up to 3 cited links).
 * Citizens get words only: no counts, latency or charts. Insurer and operator also see the call detail.
 * No run, or a run without a web call: an honest empty state.
 */
export function WebCheckCard({ stack, desk }: { stack: StackData; desk: "citizen" | "insurer" | "operator" }) {
  const run = stack.stackRun;
  const v = webCheckView(run ? webContextOf(run.raw) : null);
  const detailed = desk !== "citizen";
  return (
    <DeskCard label="Web check · Tavily" title="Was this checked against the web?">
      <p>
        {run && <DataBadge kind={run.kind} />} {v.headline}
        {v.verdict && (
          <>
            {" "}
            <span className={`webcheck-verdict webcheck-verdict--${v.verdict === "conflicts" ? "conflicts" : "other"}`}>{v.verdict}</span>
          </>
        )}
      </p>
      {detailed && v.detail && (
        <p className="note">
          {v.detail}
          {v.retrievedAt ? ` · retrieved ${v.retrievedAt}` : ""}
        </p>
      )}
      {v.links.length > 0 && (
        <ul className="webcheck-links">
          {v.links.map((l) => (
            <li key={l.url}>
              <SafeLink href={l.url}>{l.title}</SafeLink>
            </li>
          ))}
        </ul>
      )}
      <p className="note">{WEB_NOT_WARNING}.</p>
    </DeskCard>
  );
}
