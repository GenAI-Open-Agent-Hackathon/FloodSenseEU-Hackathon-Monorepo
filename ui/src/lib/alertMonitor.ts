import type { AskContext } from "./askContext";
import { fromGauge, fromModel, type EuWatchRow, type WatchSource } from "./euWatch";
import { isLiveGauge, type GaugeStatus, type GaugeSummary } from "./gauges";
import { upstreamFor } from "./sources";
import type { Reference } from "./references";

/**
 * Live alert monitor (insurer Alerts). Every watched source at Watch or Warning, read from the same views as
 * the Now page: PEGELONLINE gauges banded against their official MHW (gauge_levels.band) and GloFAS model
 * points banded against their own recent series (eu_watch.band, a model). Nothing here starts a run.
 */
export type AlertLevel = "watch" | "warning";

export const LEVEL_OF: Partial<Record<GaugeStatus, AlertLevel>> = { near: "watch", over: "warning" };
export const LEVEL_TEXT: Record<AlertLevel, string> = { watch: "Watch", warning: "Warning" };

export interface AlertRow {
  id: string;
  source: WatchSource;
  level: AlertLevel;
  /** "Official gauge vs MHW" or "Model band (GloFAS) · not an official warning". */
  basis: string;
  /** ISO time of the reading (gauge) or the model's as-of date. */
  at: string | null;
  refs: Reference[];
  /** Gauge station shortname (PEGELONLINE), for the run context. */
  station: string | null;
}

export interface MonitorInput {
  gauges: readonly GaugeSummary[];
  points: readonly EuWatchRow[];
  gaugeQueryId?: string | null;
  modelQueryId?: string | null;
  /** Views that could not be read (e.g. "GloFAS points"); the headline never says "all" while one is missing. */
  missing?: readonly string[];
}

function gaugeRef(g: GaugeSummary, queryId: string | null): Reference {
  return {
    n: 1,
    key: `gauge:${g.station}`,
    anchor: "",
    kind: "zetaris",
    heading: "Data via Zetaris",
    title: "floodsense.gauge_levels",
    layer: "a",
    publisher: "WSV, PEGELONLINE",
    licence: "DL-DE-Zero-2.0",
    attribution: "Quelle: WSV, PEGELONLINE",
    page: null,
    paragraph: null,
    quote: `${g.station} (${g.water}): ${Math.round(g.levelCm)} cm${g.warningLevelCm ? ` against MHW ${Math.round(g.warningLevelCm)} cm` : ""} at ${g.measuredAt}.`,
    queryId,
    view: "floodsense.gauge_levels",
    link: upstreamFor("gauge_levels"),
  };
}

function modelRef(r: EuWatchRow, queryId: string | null): Reference {
  return {
    n: 1,
    key: `model:${r.point_id}`,
    anchor: "",
    kind: "zetaris",
    heading: "Data via Zetaris",
    title: "floodsense.eu_watch",
    layer: "a",
    publisher: "Open-Meteo (GloFAS)",
    licence: "CC BY 4.0",
    attribution: "Weather data by Open-Meteo.com",
    page: null,
    paragraph: null,
    quote:
      r.forecast_max_m3s === null
        ? `${r.name} (${r.river}): no model reading.`
        : `${r.name} (${r.river}): 7-day forecast max ${Math.round(r.forecast_max_m3s)} m³/s${r.past30_median_m3s !== null ? ` vs past-30-day median ${Math.round(r.past30_median_m3s)} m³/s` : ""}${r.as_of_date ? `, as of ${r.as_of_date}` : ""}.`,
    queryId,
    view: "floodsense.eu_watch",
    link: upstreamFor("eu_watch"),
  };
}

/** Pure: total watched sources with a position (what the Now map draws). */
export function watchedCount(input: MonitorInput): number {
  return input.gauges.filter((g) => g.lat !== null && g.lon !== null).length + input.points.length;
}

/**
 * Pure: the alert rows. Only live sources count: a stale or seed gauge reading, or a seed model row, is never
 * raised as an alert (it is counted in `notLive` instead). Warning first, then by ratio, highest first.
 */
export function elevatedSources(input: MonitorInput): { rows: AlertRow[]; notLive: number } {
  const rows: AlertRow[] = [];
  let notLive = 0;
  for (const g of input.gauges) {
    const s = fromGauge(g);
    const level = s ? LEVEL_OF[s.status] : undefined;
    if (!s || !level) continue;
    if (!isLiveGauge(g)) {
      notLive += 1;
      continue;
    }
    rows.push({
      id: s.id,
      source: s,
      level,
      basis: "Official gauge vs MHW (PEGELONLINE)",
      at: g.measuredAt,
      refs: [gaugeRef(g, input.gaugeQueryId ?? null)],
      station: g.station,
    });
  }
  for (const p of input.points) {
    const s = fromModel(p);
    const level = LEVEL_OF[s.status];
    if (!level) continue;
    if (!s.live) {
      notLive += 1;
      continue;
    }
    rows.push({
      id: s.id,
      source: s,
      level,
      basis: "Model band (GloFAS) · not an official warning",
      at: p.as_of_date,
      refs: [modelRef(p, input.modelQueryId ?? null)],
      station: null,
    });
  }
  rows.sort(
    (a, b) =>
      (a.level === b.level ? 0 : a.level === "warning" ? -1 : 1) ||
      (b.source.ratio ?? -1) - (a.source.ratio ?? -1) ||
      a.source.name.localeCompare(b.source.name),
  );
  return { rows, notLive };
}

/** "11:42 UTC". */
export function hhmm(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} UTC`;
}

export type MonitorView =
  | { kind: "loading"; text: string }
  | { kind: "unavailable"; text: string }
  | { kind: "calm"; text: string; total: number; notLive: number }
  | { kind: "alerts"; text: string; rows: AlertRow[]; total: number; notLive: number };

/**
 * Pure: the monitor's headline. Calm says how many sources were checked and when; it says "below watch level"
 * only for sources that have a band, and names the rest.
 */
export function monitorView(
  input: MonitorInput & { state: "loading" | "rows" | "empty" | "unavailable"; checkedAt: number | null },
): MonitorView {
  if (input.state === "loading") return { kind: "loading", text: "Checking the watched sources…" };
  const total = watchedCount(input);
  if (input.state === "unavailable" && total === 0) {
    return { kind: "unavailable", text: "The live views could not be read. No alert can be shown until they answer." };
  }
  if (total === 0) return { kind: "unavailable", text: "The live views returned no sources yet." };
  const { rows, notLive } = elevatedSources(input);
  const at = input.checkedAt !== null ? ` · checked ${hhmm(input.checkedAt)}` : "";
  const gap = input.missing?.length ? ` · ${input.missing.join(" and ")} could not be read` : "";
  if (rows.length > 0) {
    const w = rows.filter((r) => r.level === "warning").length;
    const parts = [w && `${w} at Warning`, rows.length - w && `${rows.length - w} at Watch`].filter(Boolean).join(", ");
    return { kind: "alerts", text: `${parts} of ${total} watched sources${at}${gap}`, rows, total, notLive };
  }
  const banded = [
    ...input.gauges.filter((g) => g.lat !== null && g.lon !== null).map((g) => g.status),
    ...input.points.map((p) => p.band),
  ];
  const unknown = banded.filter((s) => s === "unknown").length;
  if (gap) {
    return { kind: "calm", text: `None of the ${total} sources read is at watch level${at}${gap}`, total, notLive };
  }
  const text =
    unknown === 0
      ? `All ${total} watched sources are below watch level${at}`
      : `No watched source is at watch level: ${total - unknown} of ${total} below, ${unknown} without a threshold${at}`;
  return { kind: "calm", text, total, notLive };
}

const STATION_OK = /^[A-Za-zÄÖÜäöüß .-]{2,40}$/;
const PLACE_OK = /^[\p{L}\p{N}_ .,'()-]{1,64}$/u;

/** Pure: the question for "Ask the agents to assess". Names insured sites, so the router takes the full lane. */
export function assessQuestion(row: Pick<AlertRow, "source" | "level">): string {
  const s = row.source;
  const what = s.kind === "gauge" ? `the gauge at ${LEVEL_TEXT[row.level]} level (${s.value})` : `the GloFAS model at ${LEVEL_TEXT[row.level]} band (${s.value})`;
  return `Assess the flood risk to our insured sites near ${s.name} on the ${s.river} right now: ${what}. What should the insurer do?`;
}

/**
 * Pure: the run `context` for an assessment. The agents' RunContext forbids unknown keys and checks each
 * pattern, so a station name with digits or brackets (e.g. "FRANKFURT1 (ODER)") is left out rather than refused.
 */
export function assessContext(row: Pick<AlertRow, "source" | "station">): AskContext {
  const ctx: AskContext = { role: "insurer", page: "alerts" };
  if (PLACE_OK.test(row.source.name)) ctx.place = row.source.name;
  if (row.station && STATION_OK.test(row.station)) ctx.station = row.station;
  return ctx;
}
