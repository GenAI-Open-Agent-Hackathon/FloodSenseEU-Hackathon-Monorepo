interface Entry<T> {
  value: T;
  storedAt: number;
}

/**
 * Small time-based cache with in-flight de-duplication: concurrent callers
 * for the same key share one request, so the upstream API is never hammered.
 */
export class TtlCache<T> {
  private readonly entries = new Map<string, Entry<T>>();
  private readonly inFlight = new Map<string, Promise<T>>();

  constructor(private readonly ttlMs: number) {}

  /** Returns a fresh cached value or null. */
  peek(key: string): { value: T; storedAt: number } | null {
    const entry = this.entries.get(key);
    if (!entry || Date.now() - entry.storedAt >= this.ttlMs) {
      return null;
    }
    return entry;
  }

  /** Returns the cached value, or runs `load` once and caches its result. Failures are not cached. */
  async getOrLoad(key: string, load: () => Promise<T>): Promise<{ value: T; storedAt: number; fromCache: boolean }> {
    const cached = this.peek(key);
    if (cached) {
      return { ...cached, fromCache: true };
    }
    let pending = this.inFlight.get(key);
    if (!pending) {
      pending = load()
        .then((value) => {
          this.entries.set(key, { value, storedAt: Date.now() });
          return value;
        })
        .finally(() => this.inFlight.delete(key));
      this.inFlight.set(key, pending);
    }
    const value = await pending;
    return { value, storedAt: this.entries.get(key)?.storedAt ?? Date.now(), fromCache: false };
  }
}
