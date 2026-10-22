import { useNow } from "../../hooks/useNow";
import { formatTime, minutesUntilExpiry } from "../../lib/format";
import type { CacheInfo } from "../../types";

/** Shows whether an answer is live or cached. Cached output is never labelled live. */
export function CacheLabel({ cache }: { cache: CacheInfo }) {
  const now = useNow();
  const expiresIn = minutesUntilExpiry(cache.cachedAt, cache.ttlSeconds, now);

  if (cache.source === "live") {
    return (
      <span className="cache-label cache-label--live" title={`Computed at ${formatTime(cache.cachedAt)}; cached for ${cache.ttlSeconds / 60} min`}>
        <span className="dot" aria-hidden="true" /> live · computed {formatTime(cache.cachedAt)}
      </span>
    );
  }
  return (
    <span className="cache-label cache-label--cached" title="Served from cache, not recomputed">
      cached at {formatTime(cache.cachedAt)}, {expiresIn > 0 ? `expires in ${expiresIn} min` : "expired"}
    </span>
  );
}
