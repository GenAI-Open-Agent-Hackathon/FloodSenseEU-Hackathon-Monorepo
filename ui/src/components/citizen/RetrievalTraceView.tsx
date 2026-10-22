import { getCitations } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { numberCitations } from "../../lib/citationNumbers";
import type { Claim, DiscardReason, RetrievalTrace } from "../../types";
import { CitationMarker } from "../citations/CitationMarker";

const discardLabels: Record<DiscardReason, string> = {
  outdated: "Outdated",
  "low-relevance": "Low relevance",
  "licence-pointer-only": "Licence: pointer only",
  duplicate: "Duplicate",
  "out-of-region": "Out of region",
};

/** "Why this source": every candidate the retriever returned, used or discarded, with a reason. */
export function RetrievalTraceView({ trace, claims }: { trace: RetrievalTrace; claims: readonly Claim[] }) {
  const numbers = numberCitations(claims);
  const ids = trace.candidates.flatMap((c) => (c.citationId ? [c.citationId] : []));
  const citations = useAsync(() => getCitations(ids), [ids.join(",")]);
  const byId = new Map(citations.status === "success" ? citations.data.map((c) => [c.id, c]) : []);
  const sorted = [...trace.candidates].sort((a, b) => Number(b.used) - Number(a.used) || b.relevance - a.relevance);

  return (
    <section className="retrieval" aria-label="Why these sources">
      <p className="muted small">
        Query: <code>{trace.query}</code> · top {trace.topK} · threshold {trace.relevanceThreshold.toFixed(2)} · sample trace
      </p>
      <ol className="retrieval__list">
        {sorted.map((candidate) => {
          const citation = candidate.citationId ? byId.get(candidate.citationId) : undefined;
          const number = candidate.citationId ? numbers.get(candidate.citationId) : undefined;
          return (
            <li key={candidate.id} className={`retrieval__item ${candidate.used ? "is-used" : "is-discarded"}`}>
              <div className="retrieval__score" aria-label={`Relevance ${candidate.relevance.toFixed(2)}`}>
                <span className="retrieval__bar">
                  <span style={{ width: `${Math.round(candidate.relevance * 100)}%` }} className={candidate.relevance < trace.relevanceThreshold ? "is-below" : undefined} />
                </span>
                {candidate.relevance.toFixed(2)}
              </div>
              <div className="retrieval__body">
                <div className="retrieval__title">
                  {citation && number !== undefined && <CitationMarker citation={citation} number={number} />}
                  <strong>{candidate.title}</strong>
                  <span className="muted small">
                    {candidate.publisher} · {new Date(candidate.publishedAt).getFullYear()}
                  </span>
                </div>
                <div className="retrieval__decision">
                  {candidate.used ? <span className="status status--approved">Used</span> : <span className="status status--rejected">Discarded{candidate.discardReason ? `: ${discardLabels[candidate.discardReason]}` : ""}</span>}
                  <span className="small">{candidate.note}</span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
