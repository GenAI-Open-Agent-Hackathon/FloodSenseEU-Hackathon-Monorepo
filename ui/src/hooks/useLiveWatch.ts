import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchEuWatch, type EuWatchLoad } from "../api/euWatch";
import { fetchHazardNow, type HazardNowResult } from "../api/now";
import { BAND_ELEVATED_M3S, SIMULATED_ALERT_M3S } from "../config/scenario";
import { useConsole } from "../context/ConsoleContext";
import { buildSources, fromValencia, type WatchSource } from "../lib/euWatch";
import { summariseGauges, type GaugeSummary } from "../lib/gauges";
import { summariseAll, type PointNow } from "../lib/now";
import { isDemo } from "../lib/demo";
import { oldestFetch } from "../lib/places";
import { useGaugeLevels, type GaugeState } from "./useGaugeLevels";

const REFRESH_MS = 5 * 60_000;

export type HazardLoad =
  | { state: "loading" }
  | { state: "error"; detail: string }
  | { state: "ready"; data: HazardNowResult; fetchedAt: number; demo?: boolean };

export interface EuLoad extends EuWatchLoad {
  fetchedAt: number | null;
  demo?: boolean;
}

interface Shared<T> {
  at: number;
  demo: boolean;
  request: Promise<T>;
}
let euShared: Shared<EuWatchLoad> | null = null;
let hazardShared: Shared<HazardNowResult> | null = null;

function loadEu(now: number, force: boolean): Promise<EuWatchLoad> {
  if (force || !euShared || euShared.demo !== isDemo() || now - euShared.at >= REFRESH_MS) {
    const request = fetchEuWatch();
    euShared = { at: now, demo: isDemo(), request };
    void request.then((r) => {
      if (r.state !== "rows" && euShared?.request === request) euShared = null;
    });
  }
  return euShared.request;
}

function loadHazard(now: number, force: boolean): Promise<HazardNowResult> {
  if (force || !hazardShared || hazardShared.demo !== isDemo() || now - hazardShared.at >= REFRESH_MS) {
    const request = fetchHazardNow(new AbortController().signal);
    hazardShared = { at: now, demo: isDemo(), request };
    request.catch(() => {
      if (hazardShared?.request === request) hazardShared = null;
    });
  }
  return hazardShared.request;
}

export interface LiveWatch {
  gauges: GaugeState;
  gaugeSummaries: GaugeSummary[];
  euWatch: EuLoad;
  hazard: HazardLoad;
  valencia: PointNow[];
  /** Every live-watch source: PEGELONLINE gauges, eu_watch GloFAS points, Valencia hazard_now points. */
  sources: WatchSource[];
  refresh: () => void;
  /** Oldest fetch time of the loaded views (ms), or null. */
  updatedAt: number | null;
}

/** Valencia demo cuts (config/scenario.ts): elevated -> Watch, the 80 m³/s demo alert line -> Warning. */
export const VALENCIA_CUTS = { watch: BAND_ELEVATED_M3S, warning: SIMULATED_ALERT_M3S };

/** The live views behind the citizen pages and Now, read once and shared for five minutes. */
export function useLiveWatch(): LiveWatch {
  const { points, demo, reportChecked, reportLiveFailed } = useConsole();
  const [tick, setTick] = useState(0);
  const gauges = useGaugeLevels(tick, demo);
  const gaugeSummaries = useMemo(() => summariseGauges(gauges.rows), [gauges.rows]);
  const [euWatch, setEuWatch] = useState<EuLoad>({ state: "loading", rows: [], detail: "", queryId: null, fetchedAt: null });
  const [hazard, setHazard] = useState<HazardLoad>({ state: "loading" });

  const run = useCallback((force: boolean, alive: () => boolean) => {
    const now = Date.now();
    void loadEu(now, force).then((r) => {
      if (!alive()) return;
      // A failed refresh keeps the last good rows on screen.
      setEuWatch((prev) =>
        r.state === "rows" ? { ...r, fetchedAt: Date.now(), demo: isDemo() } : prev.state !== "rows" ? { ...r, fetchedAt: null } : prev,
      );
    });
    loadHazard(now, force)
      .then((data) => {
        if (alive()) setHazard({ state: "ready", data, fetchedAt: Date.now(), demo: isDemo() });
      })
      .catch((error: unknown) => {
        if (!alive()) return;
        setHazard((prev) =>
          prev.state === "ready" ? prev : { state: "error", detail: error instanceof Error ? error.message : "request failed" },
        );
      });
  }, []);

  useEffect(() => {
    let alive = true;
    // Live and demo rows are never mixed: a switch starts both views from "loading".
    setEuWatch((prev) => (prev.state === "rows" && Boolean(prev.demo) !== demo ? { state: "loading", rows: [], detail: "", queryId: null, fetchedAt: null } : prev));
    setHazard((prev) => (prev.state === "ready" && Boolean(prev.demo) !== demo ? { state: "loading" } : prev));
    run(tick > 0, () => alive);
    const timer = window.setInterval(() => run(false, () => alive), REFRESH_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [run, tick, demo]);

  const valencia = useMemo(() => (hazard.state === "ready" ? summariseAll(hazard.data.rows) : []), [hazard]);
  const sources = useMemo(() => {
    const out = buildSources(gaugeSummaries, euWatch.rows);
    for (const summary of valencia) {
      const p = points.find((x) => x.point_id === summary.point_id);
      if (p) out.push(fromValencia(p, summary, VALENCIA_CUTS));
    }
    return out;
  }, [gaugeSummaries, euWatch.rows, valencia, points]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);
  const updatedAt = oldestFetch([
    gauges.state === "rows" ? (gauges.fetchedAt ?? null) : null,
    euWatch.state === "rows" ? euWatch.fetchedAt : null,
    hazard.state === "ready" ? hazard.fetchedAt : null,
  ]);
  useEffect(() => {
    if (updatedAt !== null) reportChecked(updatedAt);
  }, [updatedAt, reportChecked]);
  const allFailed = gauges.state === "unavailable" && euWatch.state === "unavailable" && hazard.state === "error";
  useEffect(() => {
    reportLiveFailed(allFailed);
  }, [allFailed, reportLiveFailed]);
  return { gauges, gaugeSummaries, euWatch, hazard, valencia, sources, refresh, updatedAt };
}
