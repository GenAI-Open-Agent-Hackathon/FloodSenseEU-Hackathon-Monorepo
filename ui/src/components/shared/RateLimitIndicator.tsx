import { useSyncExternalStore } from "react";
import { getRateLimitSnapshot, subscribeRateLimit } from "../../api/client";
import { useNow } from "../../hooks/useNow";

export function RateLimitIndicator() {
  const state = useSyncExternalStore(subscribeRateLimit, getRateLimitSnapshot);
  const now = useNow(1000);
  const resetIn = Math.max(0, Math.ceil((Date.parse(state.resetAt) - now) / 1000));
  const ratio = state.remaining / state.limit;
  const tone = ratio > 0.5 ? "ok" : ratio > 0.2 ? "warn" : "danger";

  return (
    <div className={`rate-limit rate-limit--${tone}`} title="Agent calls allowed per minute. Cached answers do not count.">
      <span className="rate-limit__label">Agent calls</span>
      <span className="rate-limit__meter" aria-hidden="true">
        <span style={{ width: `${ratio * 100}%` }} />
      </span>
      <span className="rate-limit__value">
        {state.remaining}/{state.limit} · resets {resetIn}s
      </span>
    </div>
  );
}
