import type { DataOrigin } from "../types/views";

export interface AdoptedView<T> {
  rows: T[];
  origin: DataOrigin;
  detail: string;
}

function sourceOf(row: unknown): string | null {
  if (!row || typeof row !== "object" || !("source" in row)) return null;
  const source = (row as { source: unknown }).source;
  return typeof source === "string" ? source : null;
}

/**
 * Seed when any adopted row is seed-stamped. A mix is not Live.
 * An empty view response, or rows with no source stamp, is live.
 */
export function originForRows(rows: unknown[]): "seed" | "live" {
  if (rows.some((row) => (sourceOf(row) ?? "").startsWith("seed:"))) return "seed";
  return "live";
}

/**
 * Health failure, or a body that is not a valid row array, keeps the fixture.
 * A valid array is adopted only from that view response. [] is an empty view, not a miss.
 * GET /health on its own never selects live or seed.
 */
export function adoptView<T>(input: {
  healthOk: boolean;
  parsed: T[] | null;
  fixtureRows: T[];
  fixtureDetail: string;
  missDetail: string;
}): AdoptedView<T> {
  if (!input.healthOk || input.parsed === null) {
    const detail = input.healthOk
      ? `${input.fixtureDetail} ${input.missDetail}.`
      : input.fixtureDetail;
    return { rows: input.fixtureRows, origin: "fixture", detail };
  }
  const origin = originForRows(input.parsed);
  const detail =
    input.parsed.length === 0 ? `${input.missDetail} · 0 rows` : `${input.missDetail} · ${origin}`;
  return { rows: input.parsed, origin, detail };
}

/** Sibling views have no source stamp. A seed discharge response marks them seed too. */
export function markBatchSeed<T>(discharge: AdoptedView<unknown>, slice: AdoptedView<T>): AdoptedView<T> {
  if (discharge.origin === "seed" && slice.origin === "live") {
    const detail = slice.detail.endsWith(" · live")
      ? `${slice.detail.slice(0, -" · live".length)} · seed`
      : slice.detail;
    return { ...slice, origin: "seed", detail };
  }
  return slice;
}
