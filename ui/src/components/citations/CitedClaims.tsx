import { getCitations } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { numberCitations } from "../../lib/citationNumbers";
import type { Citation, Claim } from "../../types";
import { CitationMarker } from "./CitationMarker";

interface CitedClaimsProps {
  claims: readonly Claim[];
  /** "list" renders one claim per bullet; "prose" renders flowing sentences. */
  variant?: "list" | "prose";
  showSources?: boolean;
}

/** Renders claims with numbered citation markers and an optional sources list. */
export function CitedClaims({ claims, variant = "list", showSources = true }: CitedClaimsProps) {
  const numbers = numberCitations(claims);
  const ids = [...numbers.keys()];
  const state = useAsync(() => getCitations(ids), [ids.join(",")]);
  const byId = new Map<string, Citation>(state.status === "success" ? state.data.map((c) => [c.id, c]) : []);

  const renderClaim = (claim: Claim) => (
    <>
      <span className={claim.support && claim.support !== "supported" ? `claim--${claim.support}` : undefined}>{claim.text}</span>
      {claim.support && claim.support !== "supported" && (
        <span className={`support-tag support-tag--${claim.support}`} title={claim.judgeNote}>
          {claim.support === "contradicted" ? "contradicted by sources" : "unsupported"}
        </span>
      )}
      {claim.citationIds.length === 0 && claim.support === undefined ? (
        <span className="uncited" title="No source supports this sentence; the Judge lowers the score">uncited · general guidance</span>
      ) : claim.citationIds.length === 0 ? null : (
        <span className="citation-markers">
          {claim.citationIds.map((id) => {
            const citation = byId.get(id);
            const number = numbers.get(id) ?? 0;
            return citation ? <CitationMarker key={id} citation={citation} number={number} /> : <span key={id} className="citation-marker is-pending">{number}</span>;
          })}
        </span>
      )}
    </>
  );

  return (
    <div className="cited-claims">
      {variant === "list" ? (
        <ul className="claims">
          {claims.map((claim) => (
            <li key={claim.id}>
              {renderClaim(claim)}
              {claim.judgeNote && <span className="judge-note">Judge: {claim.judgeNote}</span>}
            </li>
          ))}
        </ul>
      ) : (
        <p className="claims-prose">
          {claims.map((claim) => (
            <span key={claim.id}>
              {renderClaim(claim)}
              {claim.judgeNote && <span className="judge-note">Judge: {claim.judgeNote}</span>}{" "}
            </span>
          ))}
        </p>
      )}
      {showSources && byId.size > 0 && (
        <ol className="sources">
          {ids.map((id) => {
            const citation = byId.get(id);
            return citation ? (
              <li key={id} value={numbers.get(id)}>
                <SourceLine citation={citation} number={numbers.get(id) ?? 0} />
              </li>
            ) : null;
          })}
        </ol>
      )}
    </div>
  );
}

function SourceLine({ citation, number }: { citation: Citation; number: number }) {
  return (
    <span className="source-line">
      <CitationMarker citation={citation} number={number} />
      <span className="source-line__title">{citation.title}</span>
      <span className="source-line__publisher">{citation.publisher}</span>
      {citation.zetaris && <span className="chip chip--zetaris">Zetaris</span>}
    </span>
  );
}
