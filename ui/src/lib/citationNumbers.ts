import type { Claim } from "../types";

/**
 * Assigns display numbers [1], [2], ... to citations in order of first
 * appearance across a list of claims, like footnotes in a report.
 */
export function numberCitations(claims: readonly Claim[]): Map<string, number> {
  const numbers = new Map<string, number>();
  for (const claim of claims) {
    for (const id of claim.citationIds) {
      if (!numbers.has(id)) {
        numbers.set(id, numbers.size + 1);
      }
    }
  }
  return numbers;
}
