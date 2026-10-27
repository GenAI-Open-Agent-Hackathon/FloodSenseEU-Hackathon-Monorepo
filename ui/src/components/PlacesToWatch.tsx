import { useMemo, useState } from "react";
import type { LiveWatch } from "../hooks/useLiveWatch";
import type { WatchSource } from "../lib/euWatch";
import { evidenceForSource, type LiveEvidence, type ViewMeta } from "../lib/liveEvidence";
import { basisLabel, calmSentence, plainOf, STATUS_WORD, worstFirst, type PlainStatus } from "../lib/places";
import { LiveSourceBadge } from "./LiveSources";

/** Query id and fetch time of the view behind one source kind. */
export function metaFor(live: Pick<LiveWatch, "gauges" | "euWatch" | "hazard">, kind: WatchSource["kind"]): ViewMeta {
  if (kind === "gauge") {
    const g = live.gauges as { queryId?: string | null; executedAt?: string | null };
    return { queryId: g.queryId ?? null, executedAt: g.executedAt ?? null };
  }
  if (kind === "model") return { queryId: live.euWatch.queryId, executedAt: live.euWatch.executedAt, fetchedAt: live.euWatch.fetchedAt };
  return live.hazard.state === "ready"
    ? { queryId: live.hazard.data.queryId, executedAt: live.hazard.data.executedAt, fetchedAt: live.hazard.fetchedAt }
    : { queryId: null };
}

export function evidenceFor(live: Pick<LiveWatch, "gauges" | "euWatch" | "hazard">, s: WatchSource): LiveEvidence {
  return evidenceForSource(s, metaFor(live, s.kind));
}

export function StatusChip({ status }: { status: PlainStatus }) {
  return <span className={`plain-chip plain-chip--${status}`}>{STATUS_WORD[status]}</span>;
}

function measured(iso: string | null): string {
  if (!iso) return "time not given";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return iso.length === 10
    ? `model day ${d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })}`
    : `measured ${d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC" })} UTC`;
}

/** One row: plain status, one calm line, a numbered source; the number itself only under Details. */
export function PlaceRow({ s, n, live, onAsk }: { s: WatchSource; n: number; live: LiveWatch; onAsk?: (s: WatchSource) => void }) {
  const status = plainOf(s);
  const title = s.river ? `${s.river} · ${s.name}` : s.name;
  return (
    <li className={`ptw-row ptw-row--${status}`}>
      <div className="ptw-row__head">
        <StatusChip status={status} />
        <strong className="ptw-row__name">{title}</strong>
        <span className="muted small">{s.country}</span>
      </div>
      <p className="ptw-row__line">
        {calmSentence(s.kind, status, s.river, s.name)} <LiveSourceBadge n={n} evidence={evidenceFor(live, s)} />
      </p>
      <details className="disclosure ptw-row__details">
        <summary>Details</summary>
        <p className="note">
          {s.value} · {basisLabel(s.kind)} · {measured(s.measuredAt)} · {s.live ? "live" : "not live (stale or seed)"}
        </p>
        {onAsk && (
          <button type="button" className="link-button" onClick={() => onAsk(s)}>
            Ask FloodSense about {s.name}
          </button>
        )}
      </details>
    </li>
  );
}

const SHORT = 8;

/** "Places to watch": worst first, short by default, all on request. */
export function PlacesToWatch({
  live,
  onAsk,
  limit = SHORT,
  title = "Places to watch",
}: {
  live: LiveWatch;
  onAsk?: (s: WatchSource) => void;
  limit?: number;
  title?: string;
}) {
  const [all, setAll] = useState(false);
  const sorted = useMemo(() => worstFirst(live.sources), [live.sources]);
  const shown = all ? sorted : sorted.slice(0, limit);
  if (sorted.length === 0) return <p className="note">No live readings yet.</p>;
  return (
    <section className="ptw" aria-label={title}>
      <h3 className="section-title">{title}</h3>
      <ol className="ptw-list">
        {shown.map((s, i) => (
          <PlaceRow key={s.id} s={s} n={i + 1} live={live} onAsk={onAsk} />
        ))}
      </ol>
      {sorted.length > limit && (
        <button type="button" className="button ghost" aria-expanded={all} onClick={() => setAll((v) => !v)}>
          {all ? "Show fewer" : `Show all ${sorted.length} places`}
        </button>
      )}
    </section>
  );
}
