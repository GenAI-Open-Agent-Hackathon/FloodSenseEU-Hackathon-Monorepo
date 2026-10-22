import type { DataProvenance } from "../../types";

const labels: Record<DataProvenance, string> = {
  live: "Live",
  sample: "Sample",
  reconstructed: "Reconstructed sample",
};

const titles: Record<DataProvenance, string> = {
  live: "Fetched from the provider just now (or within the 5-minute cache)",
  sample: "Invented sample values for the mock, not real measurements",
  reconstructed: "Reconstructed sample, not real measurements",
};

/** Labels where a value came from. Anything not live is clearly marked. */
export function ProvenanceBadge({ provenance, detail }: { provenance: DataProvenance; detail?: string }) {
  return (
    <span className={`provenance provenance--${provenance}`} title={titles[provenance]}>
      {provenance === "live" && <span className="dot" aria-hidden="true" />}
      {labels[provenance]}
      {detail && <span className="provenance__detail"> · {detail}</span>}
    </span>
  );
}
