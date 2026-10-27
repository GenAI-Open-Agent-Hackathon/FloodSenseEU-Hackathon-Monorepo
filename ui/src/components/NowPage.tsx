import { useEffect, useState } from "react";
import { NEXT_48H_QUESTION } from "../api/ask";
import { useConsole } from "../context/ConsoleContext";
import { useLiveWatch } from "../hooks/useLiveWatch";
import type { WatchSource } from "../lib/euWatch";
import { relativeTime } from "../lib/now";
import { statusCounts } from "../lib/places";
import { EuWatchLegend, EuWatchList, EuWatchMap } from "./EuWatch";
import { PlacesToWatch } from "./PlacesToWatch";

/**
 * Live page: ONE Europe map with every live-watch source (PEGELONLINE gauges, eu_watch GloFAS points and the
 * Valencia hazard_now points), coloured by plain status, then "Places to watch", worst first. Numbers live under
 * Details; every row has a numbered source that opens the Evidence drawer. Insurers also get the sortable list.
 */
export function NowPage() {
  const { openAsk, route } = useConsole();
  const live = useLiveWatch();
  const [clock, setClock] = useState(() => Date.now());
  useEffect(() => {
    const tick = window.setInterval(() => setClock(Date.now()), 30_000);
    return () => window.clearInterval(tick);
  }, []);

  const counts = statusCounts(live.sources);
  const gauges = live.sources.filter((s) => s.kind === "gauge").length;
  const model = live.sources.filter((s) => s.kind === "model").length;
  const valencia = live.sources.length - gauges - model;
  const fetchedAt = live.euWatch.fetchedAt ?? (live.hazard.state === "ready" ? live.hazard.fetchedAt : null);
  const loading = live.gauges.state === "loading" && live.euWatch.state === "loading" && live.hazard.state === "loading";
  const ask = (s: WatchSource) => openAsk(s.question, { page: "now", place: s.name });

  return (
    <div className="now-page">
      <header className="now-head">
        <div>
          <h2 className="now-title">Right now, across our watch</h2>
          <p className="now-meta" aria-live="polite">
            <span className="now-live-tag">Live data · Zetaris</span>
            {fetchedAt ? ` Updated ${relativeTime(fetchedAt, clock)}` : ""}
            {live.sources.length > 0
              ? ` · ${counts.warning} warning · ${counts.watch} watch · ${counts.normal} normal${counts.unknown ? ` · ${counts.unknown} no reading` : ""}`
              : ""}
          </p>
        </div>
        <div className="button-row">
          <button type="button" className="now-refresh" onClick={() => openAsk(NEXT_48H_QUESTION)}>
            Ask about the next 48 hours
          </button>
          <button type="button" className="now-refresh" onClick={live.refresh}>
            Refresh
          </button>
        </div>
      </header>

      <section className="now-region" aria-labelledby="now-eu">
        <div className="now-region-head">
          <h3 className="now-subtitle" id="now-eu">
            Europe · live watch
          </h3>
          <span className="muted small">
            {gauges} PEGELONLINE gauges · {model} GloFAS points · {valencia} Valencia points
          </span>
        </div>
        <p className="now-note">
          Circles are measured water levels against official PEGELONLINE characteristic values (MHW). Diamonds are GloFAS
          model discharge: a model, not an official warning. Faded or dashed markers are not a fresh live reading. Click a
          place to ask about it.
        </p>
        {loading && (
          <p className="now-status" aria-live="polite">
            Loading live data…
          </p>
        )}
        {live.euWatch.state === "unavailable" && <p className="note">GloFAS points unavailable: {live.euWatch.detail}</p>}
        {live.hazard.state === "error" && <p className="note">Valencia points unavailable: {live.hazard.detail}</p>}
        {live.gauges.state === "unavailable" && <p className="note">Gauges unavailable: {live.gauges.detail}</p>}
        <EuWatchLegend />
        <EuWatchMap sources={live.sources} />
        <PlacesToWatch live={live} onAsk={ask} />
        {route === "insurer" && live.sources.length > 0 && (
          <details className="disclosure">
            <summary>All sources (sortable, with numbers)</summary>
            <EuWatchList sources={live.sources} />
          </details>
        )}
        <p className="now-source">
          Quelle: WSV, PEGELONLINE (DL-DE-Zero-2.0) · Weather data by Open-Meteo.com (GloFAS, CC BY 4.0) · via Zetaris
        </p>
      </section>
    </div>
  );
}
