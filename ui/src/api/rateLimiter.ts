import type { RateLimitState } from "../types";

/**
 * Client-side mirror of the API rate limit. The real backend will send
 * X-RateLimit-* headers; until then this simulates a fixed window.
 */
const LIMIT = 10;
const WINDOW_MS = 60_000;

let windowStart = Date.now();
let used = 0;
const listeners = new Set<() => void>();
let snapshot: RateLimitState = buildSnapshot();

function buildSnapshot(): RateLimitState {
  return { limit: LIMIT, remaining: LIMIT - used, resetAt: new Date(windowStart + WINDOW_MS).toISOString() };
}

function publish(): void {
  snapshot = buildSnapshot();
  listeners.forEach((listener) => listener());
}

function rollWindow(): void {
  if (Date.now() - windowStart >= WINDOW_MS) {
    windowStart = Date.now();
    used = 0;
    publish();
  }
}

export class RateLimitError extends Error {
  readonly retryAfterSeconds: number;

  constructor(retryAfterSeconds: number) {
    super(`Rate limit reached. Try again in ${retryAfterSeconds} s.`);
    this.name = "RateLimitError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** Consumes one request from the window or throws RateLimitError. */
export function consumeRequest(): void {
  rollWindow();
  if (used >= LIMIT) {
    const retryAfterSeconds = Math.ceil((windowStart + WINDOW_MS - Date.now()) / 1000);
    throw new RateLimitError(retryAfterSeconds);
  }
  used += 1;
  publish();
}

export function subscribeRateLimit(listener: () => void): () => void {
  listeners.add(listener);
  const timer = window.setInterval(rollWindow, 1000);
  return () => {
    listeners.delete(listener);
    window.clearInterval(timer);
  };
}

export function getRateLimitSnapshot(): RateLimitState {
  return snapshot;
}
