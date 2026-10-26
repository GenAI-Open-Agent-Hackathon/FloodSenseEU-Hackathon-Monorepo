import { servingLabel, servingQualifier } from "../lib/format";
import { statusLabel } from "../lib/origin";
import { useConsole } from "../context/ConsoleContext";
import type { ProvenanceRow } from "../types/views";

/** Answer serving line. It was the cache banner on every insurer page. It now sits under the top-bar chip. */
export function ServingLine() {
  const { answer } = useConsole();
  const serving = servingLabel(answer);
  return (
    <p className={`serving serving-${serving.kind}`} data-serving={serving.servedFrom}>
      <strong>{serving.kind === "cached" ? `${serving.text} UTC` : serving.text}</strong>
      <span>
        {" "}
        · {servingQualifier(serving)} · run {serving.runId}
      </span>
    </p>
  );
}

/** Origin of each view. It was the origin banner. It now sits under the top-bar chip and on Portfolio. */
export function OriginList() {
  const desk = useConsole();
  const parts = [
    ["discharge_daily", desk.discharge],
    ["hazard_timeline", desk.hazard],
    ["exposure_join", desk.exposure],
    ["provenance", desk.provenance],
  ] as const;
  return (
    <div className="origin-list" data-origin={parts.map(([, slice]) => slice.origin).join(" ")}>
      <dl className="kv">
        {parts.map(([name, slice]) => (
          <div key={name}>
            <dt>{name}</dt>
            <dd>
              {statusLabel(slice.origin)} · {slice.detail}
            </dd>
          </div>
        ))}
      </dl>
      <p className="note">{desk.healthDetail}</p>
    </div>
  );
}

function pick(rows: ProvenanceRow[], test: (dataset: string) => boolean): ProvenanceRow | undefined {
  return rows.find((row) => test(row.dataset.toLowerCase()));
}

export function Colophon() {
  const { provenance } = useConsole();
  const rows = provenance.rows;
  const chosen = [
    pick(rows, (name) => name.includes("glofas") || name.includes("open-meteo flood")),
    pick(rows, (name) => name.includes("emsr773")),
    pick(rows, (name) => name.includes("osm")),
    pick(rows, (name) => name.includes("synthetic")),
  ].filter((row): row is ProvenanceRow => Boolean(row));
  return (
    <footer className="colophon">
      {chosen.map((row) => (
        <p key={row.dataset}>
          {row.attribution} ({row.licence})
        </p>
      ))}
      <p>Portfolio rows are synthetic. Modelled discharge is not an official warning.</p>
    </footer>
  );
}
