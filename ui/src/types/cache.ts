/** How an answer was served. Replayed output must never be shown as live. */
export type CacheSource = "live" | "cache";

export interface CacheInfo {
  source: CacheSource;
  /** ISO 8601 timestamp when the answer was first computed and stored. */
  cachedAt: string;
  ttlSeconds: number;
}

/** Mirrors standard X-RateLimit-* response headers. */
export interface RateLimitState {
  limit: number;
  remaining: number;
  /** ISO 8601 timestamp when the window resets. */
  resetAt: string;
}
