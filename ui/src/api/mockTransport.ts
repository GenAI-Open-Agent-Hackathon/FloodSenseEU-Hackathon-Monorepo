/**
 * Helpers for mock responses. Real implementations replace calls to
 * `respond` with `fetch` and keep the same function signatures.
 */

/** Simulated network latency so loading states are visible in the mock. */
export function respond<T>(value: T, latencyMs = 150): Promise<T> {
  return new Promise((resolve) => window.setTimeout(() => resolve(structuredClone(value)), latencyMs));
}

export function notFound(kind: string, id: string): Error {
  return new Error(`${kind} not found: ${id}`);
}
