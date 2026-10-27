import { useEffect, useMemo, useState } from "react";
import { fetchEuWatch, type EuWatchLoad } from "../api/euWatch";
import { buildSources, type EuWatchRow, type WatchSource } from "../lib/euWatch";
import { summariseGauges, type GaugeSummary } from "../lib/gauges";
import { GAUGE_REFRESH_MS, useGaugeLevels } from "./useGaugeLevels";

export interface LiveWatch {
  gauges: GaugeSummary[];
  points: EuWatchRow[];
  sources: WatchSource[];
  gaugeQueryId: string | null;
  modelQueryId: string | null;
  /** loading until both views answered once; rows when either has rows. */
  state: "loading" | "rows" | "empty" | "unavailable";
  /** When the newest of the two reads finished (ms), or null before the first. */
  checkedAt: number | null;
  detail: string;
  /** Views that could not be read this time, by name. */
  missing: string[];
}

/**
 * The Europe live watch the insurer pages read: PEGELONLINE gauges (gauge_levels) and GloFAS points (eu_watch),
 * both through the Zetaris-backed API, re-read every 5 minutes like the Now page. Nothing is cached when a read fails.
 */
export function useLiveWatch(): LiveWatch {
  const gaugeLoad = useGaugeLevels();
  const [model, setModel] = useState<EuWatchLoad>({ rows: [], state: "loading", detail: "", queryId: null });
  const [modelAt, setModelAt] = useState<number | null>(null);
  const [gaugeAt, setGaugeAt] = useState<number | null>(null);

  useEffect(() => {
    if (gaugeLoad.state !== "loading") setGaugeAt(Date.now());
  }, [gaugeLoad]);

  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    const run = () =>
      void fetchEuWatch(controller.signal).then((load) => {
        if (!alive) return;
        setModel(load);
        setModelAt(Date.now());
      });
    run();
    const timer = setInterval(run, GAUGE_REFRESH_MS);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  return useMemo(() => {
    const gauges = summariseGauges(gaugeLoad.rows);
    const sources = buildSources(gauges, model.rows);
    const loading = gaugeLoad.state === "loading" || model.state === "loading";
    const any = gauges.length > 0 || model.rows.length > 0;
    const state: LiveWatch["state"] = loading ? "loading" : any ? "rows" : gaugeLoad.state === "unavailable" && model.state === "unavailable" ? "unavailable" : "empty";
    const times = [gaugeAt, modelAt].filter((t): t is number => t !== null);
    return {
      gauges,
      points: model.rows,
      sources,
      gaugeQueryId: "queryId" in gaugeLoad ? (gaugeLoad.queryId ?? null) : null,
      modelQueryId: model.queryId,
      state,
      checkedAt: times.length ? Math.max(...times) : null,
      detail: [gaugeLoad.detail, model.detail].filter(Boolean).join(" · "),
      missing: [gaugeLoad.state === "unavailable" && "PEGELONLINE gauges", model.state === "unavailable" && "GloFAS points"].filter((m): m is string => !!m),
    };
  }, [gaugeLoad, model, gaugeAt, modelAt]);
}
