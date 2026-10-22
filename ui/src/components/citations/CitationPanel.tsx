import { useEffect, useRef } from "react";
import { formatDate, formatTime } from "../../lib/format";
import type { Citation, SourceLocator } from "../../types";
import { MockBadge } from "../shared/MockBadge";
import { useCitationPanel } from "./CitationContext";

function describeLocator(locator: SourceLocator): string {
  const parts = [
    locator.section,
    locator.page !== undefined ? `page ${locator.page}` : undefined,
    locator.paragraph !== undefined ? `paragraph ${locator.paragraph}` : undefined,
    locator.lines ? `lines ${locator.lines}` : undefined,
  ];
  return parts.filter(Boolean).join(" · ") || "Whole document";
}

const isWebUrl = (url: string): boolean => url.startsWith("https://") || url.startsWith("http://");

const storageText: Record<Citation["storage"], string> = {
  "full-text": "Open source: full text stored and chunked (document → section → page → paragraph).",
  "pointer-and-quote": "Restricted source: only this pointer and the short quote are stored; the document is fetched on demand.",
};

/** Side drawer showing all three citation layers for the selected marker. */
export function CitationPanel() {
  const { active, close } = useCitationPanel();
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!active) {
      return;
    }
    closeButton.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, close]);

  if (!active) {
    return null;
  }
  const { citation, number } = active;

  return (
    <aside className="citation-panel" role="dialog" aria-modal="false" aria-labelledby="citation-panel-title">
      <header className="citation-panel__header">
        <span className="citation-panel__number">[{number}]</span>
        <h2 id="citation-panel-title">{citation.title}</h2>
        <button ref={closeButton} type="button" className="icon-button" onClick={close} aria-label="Close citation">
          ×
        </button>
      </header>

      <div className="citation-panel__body">
        <MockBadge label="MOCK CITATION · SAMPLE QUOTE" />

        <section>
          <h3>Source</h3>
          <dl className="kv">
            <dt>Publisher</dt>
            <dd>{citation.publisher}</dd>
            <dt>URL</dt>
            <dd>
              {isWebUrl(citation.url) ? (
                <a href={citation.url} target="_blank" rel="noreferrer noopener">
                  {citation.url}
                </a>
              ) : (
                <code>{citation.url}</code>
              )}
            </dd>
            <dt>Accessed</dt>
            <dd>{formatDate(citation.accessedAt)}</dd>
            <dt>Location</dt>
            <dd>{describeLocator(citation.locator)}</dd>
            <dt>Licence</dt>
            <dd>{citation.license}</dd>
          </dl>
        </section>

        <section>
          <h3>
            Quote {citation.quoteIsSample && <span className="chip chip--sample">sample text, not a real quote</span>}
          </h3>
          <blockquote className="quote">{citation.quote}</blockquote>
          <p className="hash">
            sha256 <code>{citation.contentHash}</code>
          </p>
          <p className="muted small">{storageText[citation.storage]}</p>
        </section>

        {citation.zetaris && (
          <section className="zetaris">
            <h3>
              Zetaris query <span className="chip chip--zetaris">numbers come from here</span>
            </h3>
            <dl className="kv">
              <dt>Dataset</dt>
              <dd>
                <code>{citation.zetaris.dataset}</code>
              </dd>
              <dt>Rows</dt>
              <dd>{citation.zetaris.rowCount}</dd>
              <dt>Executed</dt>
              <dd>{formatTime(citation.zetaris.executedAt)}</dd>
            </dl>
            <pre className="sql">{citation.zetaris.query}</pre>
          </section>
        )}
      </div>
    </aside>
  );
}
