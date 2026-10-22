import type { Citation } from "../../types";
import { useCitationPanel } from "./CitationContext";

/** Inline numbered marker, e.g. [2]. Opens the citation panel on click. */
export function CitationMarker({ citation, number }: { citation: Citation; number: number }) {
  const { active, open } = useCitationPanel();
  const isOpen = active?.citation.id === citation.id;
  return (
    <button
      type="button"
      className={`citation-marker ${isOpen ? "is-open" : ""}`}
      onClick={() => open(citation, number)}
      aria-label={`Citation ${number}: ${citation.title}`}
      title={citation.title}
    >
      {number}
    </button>
  );
}
