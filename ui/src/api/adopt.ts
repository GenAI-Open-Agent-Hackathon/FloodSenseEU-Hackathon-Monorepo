import type { DataOrigin } from "../types/views";

export interface AdoptedView<T> {
  rows: T[];
  origin: DataOrigin;
  detail: string;
}

/**
 * Health failure or a body that is not a valid row array keeps the fixture.
 * A valid array, including [], is live. [] is an empty view, not a miss.
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
  const detail = input.parsed.length === 0 ? `${input.missDetail} · 0 rows` : input.missDetail;
  return { rows: input.parsed, origin: "live", detail };
}
