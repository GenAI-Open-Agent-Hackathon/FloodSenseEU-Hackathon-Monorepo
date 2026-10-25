import { useEffect, useRef } from "react";
import { useConsole } from "../context/ConsoleContext";
import { useDismiss } from "../hooks/useDismiss";
import { formatCell, formatDay } from "../lib/format";
import { pointById, provenanceForSource, rowAt, sourceExplanation } from "../lib/series";
import type { Evidence } from "../types/contract";

const PREFERRED = [
  "point_id",
  "date",
  "ts_utc",
  "discharge_m3s",
  "rain_mm",
  "warning_level",
  "source",
  "policy_id",
  "site_id",
  "in_footprint",
  "sum_insured_eur",
  "segment",
  "dataset",
  "publisher",
  "licence",
];

function columnOrder(rows: Record<string, unknown>[]): string[] {
  const present = new Set(rows.flatMap((row) => Object.keys(row)));
  const first = PREFERRED.filter((key) => present.has(key));
  const rest = [...present].filter((key) => !first.includes(key));
  return [...first, ...rest];
}

function SampleTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) return <p className="note">No sample rows.</p>;
  const keys = columnOrder(rows);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key}>{key}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {keys.map((key) => (
                <td key={key}>{formatCell(row[key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  return (
    <article className="evidence-block">
      <h3>{evidence.view}</h3>
      <dl className="kv">
        <div>
          <dt>query_id</dt>
          <dd>{evidence.query_id}</dd>
        </div>
        <div>
          <dt>row_count</dt>
          <dd>{evidence.row_count}</dd>
        </div>
        <div>
          <dt>executed_at_utc</dt>
          <dd>{evidence.executed_at_utc}</dd>
        </div>
      </dl>
      <p className="note">Fixture SQL, not sent to Zetaris from this screen. query_id is not a live Zetaris id.</p>
      <pre className="sql">{evidence.sql}</pre>
      <SampleTable rows={evidence.rows_sample} />
    </article>
  );
}

export function EvidenceDrawer() {
  const desk = useConsole();
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const point = pointById(desk.points, desk.pointId);
  const row = rowAt(desk.discharge.rows, desk.pointId, desk.date);
  const dischargeProvenance = row ? provenanceForSource(row.source, desk.provenance.rows) : undefined;
  const rainProvenance = provenanceForSource("open-meteo-rain", desk.provenance.rows);
  useDismiss(desk.evidenceOpen, desk.closeEvidence, panelRef);

  useEffect(() => {
    if (!desk.evidenceOpen) return;
    closeRef.current?.focus();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const target = document.getElementById(desk.evidenceTopic === "rain" ? "why-rain" : "why-discharge");
    target?.scrollIntoView({ block: "start" });
    return () => {
      document.body.style.overflow = previous;
    };
  }, [desk.evidenceOpen, desk.evidenceTopic]);

  if (!desk.evidenceOpen) return null;

  return (
    <div className="drawer-backdrop">
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="evidence-title" ref={panelRef}>
        <div className="drawer-head">
          <div>
            <p className="section-label">Evidence</p>
            <h2 id="evidence-title">Why this source</h2>
          </div>
          <button ref={closeRef} type="button" className="button" onClick={desk.closeEvidence}>
            Close
          </button>
        </div>
        <div className="drawer-body">
          <section id="why-discharge">
            <h3>discharge_daily.source</h3>
            {row ? (
              <>
                <p>
                  {point ? `${point.name} (${row.point_id})` : row.point_id} on {formatDay(row.date)}.{" "}
                  {sourceExplanation(row.source)} Values are modelled GloFAS discharge, not observed gauge readings.
                </p>
                <dl className="kv">
                  <div>
                    <dt>source</dt>
                    <dd>{row.source}</dd>
                  </div>
                  <div>
                    <dt>discharge_m3s</dt>
                    <dd>{row.discharge_m3s}</dd>
                  </div>
                </dl>
              </>
            ) : (
              <p className="note">No discharge row is selected.</p>
            )}
            {dischargeProvenance ? (
              <ProvenanceList row={dischargeProvenance} />
            ) : (
              <p className="note">No provenance row matched this source value.</p>
            )}
          </section>
          <section id="why-rain">
            <h3>Rain and warning_level</h3>
            <p>
              Hourly rain is hazard_timeline, joined to that day’s discharge. warning_level is null in the seed and
              in the live view until another source fills it. This screen does not invent that column.
            </p>
            {rainProvenance ? (
              <ProvenanceList row={rainProvenance} />
            ) : (
              <p className="note">No rain provenance row in the loaded set.</p>
            )}
          </section>
          <section>
            <h3>Answer evidence</h3>
            <p className="note">
              These blocks follow the shared evidence contract. They were packed with the fixture answer, not queried
              live.
            </p>
            {desk.answer.evidence.map((evidence) => (
              <EvidenceBlock key={evidence.query_id} evidence={evidence} />
            ))}
          </section>
          <section>
            <h3>Citations</h3>
            <ul className="citation-list">
              {desk.answer.citations.map((citation) => (
                <li key={citation.citation_id}>
                  <p className="menu-title">
                    Layer {citation.layer} · {citation.title}
                  </p>
                  <p className="menu-body">{citation.quote}</p>
                  <p className="note">
                    {citation.publisher} · {citation.licence}
                    <br />
                    {citation.attribution}
                  </p>
                  <p className="note">
                    <a href={citation.source_url} target="_blank" rel="noreferrer">
                      {citation.source_url}
                    </a>
                  </p>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h3>provenance view</h3>
            <p className="note">
              Columns are dataset, source_url, publisher, licence, attribution, fetched_at. fetched_at is the prep
              accessed_at cast to midnight UTC. This console does not call the feeds. Listing a dataset does not
              assign an owner.
            </p>
            {desk.provenance.rows.map((item) => (
              <article key={item.dataset} className="evidence-block">
                <h3>{item.dataset}</h3>
                <ProvenanceList row={item} />
              </article>
            ))}
          </section>
        </div>
      </aside>
    </div>
  );
}

function ProvenanceList({
  row,
}: {
  row: {
    dataset: string;
    source_url: string;
    publisher: string;
    licence: string;
    attribution: string;
    fetched_at: string;
  };
}) {
  return (
    <dl className="kv">
      <div>
        <dt>dataset</dt>
        <dd>{row.dataset}</dd>
      </div>
      <div>
        <dt>publisher</dt>
        <dd>{row.publisher}</dd>
      </div>
      <div>
        <dt>licence</dt>
        <dd>{row.licence}</dd>
      </div>
      <div>
        <dt>attribution</dt>
        <dd>{row.attribution}</dd>
      </div>
      <div>
        <dt>source_url</dt>
        <dd>
          <a href={row.source_url} target="_blank" rel="noreferrer">
            {row.source_url}
          </a>
        </dd>
      </div>
      <div>
        <dt>fetched_at</dt>
        <dd>{row.fetched_at}</dd>
      </div>
    </dl>
  );
}
