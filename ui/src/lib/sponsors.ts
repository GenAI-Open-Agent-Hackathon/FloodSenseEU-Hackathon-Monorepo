import type { PlatformStatus } from "../api/platform";
import type { WebContext } from "../types/contract";
import { modelDisplay } from "./techTrace";

export const WEB_NOT_WARNING = "Web context, not an official warning";

/** One line per sponsor, each backed by the repo (docs/architecture/technical-highlights.md). */
export const WHY_SPONSOR: readonly (readonly [string, string])[] = [
  ["Nebius Token Factory", "one API for every model lane; swapping a model is a setting, not a code change."],
  ["NVIDIA Nemotron", "model sizes are mapped to lanes: a small one for fast answers, a larger one for deep reasoning."],
  ["Tavily", "live web evidence the Skeptic checks an answer against, shown as web context and never as a warning."],
  ["Zetaris", "governed SQL: agents read sensor and portfolio data only through Zetaris views and cite the query id."],
  ["Meterless", "memory (H-MEM) that learns only from approved answers; the World Model tracks which hypotheses the evidence still supports."],
];

export type ChipState = "on" | "off" | "unavailable";
export interface SponsorChip {
  id: "nebius" | "nemotron" | "tavily" | "zetaris" | "meterless";
  label: string;
  /** Second line: model ids, call count... Only what the status states. */
  detail: string | null;
  state: ChipState;
  title: string;
}

const obj = (v: unknown): Record<string, unknown> => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {});
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const text = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v : null);

const short = (id: string | undefined): string | null => (id ? modelDisplay(id).replace(/^Nemotron\s*/i, "") : null);

/** Pure: the global sponsor strip. `platform` null = /platform/status not reachable: every dot is "unavailable", never a guess. */
export function sponsorChips(platform: PlatformStatus | null): SponsorChip[] {
  const down = (on: boolean): ChipState => (!platform ? "unavailable" : on ? "on" : "off");
  const t = platform?.tavilyStatus ?? null;
  const tavilyOn = t ? t.enabled : platform?.tavily === true;
  const fast = short(platform?.lanes.fast);
  const deep = short(platform?.lanes.deep);
  const models = [fast && `fast ${fast}`, deep && `deep ${deep}`].filter(Boolean).join(" · ");
  const nebius = platform?.llmBackend === "nebius";
  return [
    {
      id: "nebius",
      label: "Nebius Token Factory",
      detail: platform?.llmBackend && !nebius ? `backend: ${platform.llmBackend}` : null,
      state: down(nebius),
      title: "One API for every model lane. Swapping a model is a setting.",
    },
    {
      id: "nemotron",
      label: "NVIDIA Nemotron",
      detail: models || null,
      state: down(Object.keys(platform?.lanes ?? {}).length > 0),
      title: "Nemotron model sizes mapped to the fast and deep lanes.",
    },
    {
      id: "tavily",
      label: "Tavily",
      detail: !platform ? null : !tavilyOn ? "off" : t ? `${t.calls} ${t.calls === 1 ? "call" : "calls"}` : "on",
      state: down(tavilyOn),
      title: "Live web evidence checked by the Skeptic. Complements Zetaris, which runs SQL on sensor and portfolio data. Web context, not an official warning.",
    },
    {
      id: "zetaris",
      label: "Zetaris",
      detail: platform ? platform.dataBackend : null,
      state: down(platform?.dataBackend === "zetaris"),
      title: "Governed SQL over sensor and portfolio data.",
    },
    {
      id: "meterless",
      label: "Meterless H-MEM / World Model",
      detail: null,
      state: down(platform?.agentsOk === true),
      title: "Memory that learns only from approved answers. Dot shows the agents process, not the memory alone.",
    },
  ];
}

export { regionBadge } from "./lanes";

export const usd = (v: number | null | undefined): string =>
  v === null || v === undefined ? "n/a" : v === 0 ? "$0" : v < 0.01 ? `$${v.toFixed(6).replace(/0+$/, "")}` : `$${v.toFixed(v < 1 ? 4 : 2)}`;

export const perM = (v: number | null | undefined): string => (v === null || v === undefined ? "n/a" : `$${v}`);

/** Pure: the Web check of a run. Reads the projected answer.web_context, else the raw agents body (web + web_check). */
export function webContextOf(raw: unknown): WebContext | null {
  const b = obj(raw);
  const direct = obj(obj(b.answer).web_context);
  const w = Object.keys(direct).length ? direct : obj(b.web);
  const status = w.status;
  if (status !== "ok" && status !== "empty" && status !== "unavailable") return null;
  const items = Array.isArray(w.results) ? w.results : Array.isArray(w.items) ? w.items : [];
  const results = items.flatMap((i) => {
    const o = obj(i);
    const url = text(o.url);
    return url ? [{ url, title: text(o.title) ?? url, retrieved_at: text(o.retrieved_at) ?? text(w.retrieved_at) }] : [];
  });
  const wcRaw = obj(direct.web_check ?? b.web_check);
  const v = wcRaw.verdict;
  return {
    status,
    query: text(w.query) ?? "",
    n_results: num(w.n_results) ?? results.length,
    latency_ms: num(w.latency_ms) ?? 0,
    cached: w.cached === true,
    retrieved_at: text(w.retrieved_at),
    results,
    ...(v === "supports" || v === "contradicts" || v === "neutral"
      ? { web_check: { claim_id: text(wcRaw.claim_id) ?? "", verdict: v, url: text(wcRaw.url) ?? "", note: text(wcRaw.note) ?? undefined } }
      : {}),
  };
}

export const VERDICT_WORD = { supports: "confirmed", contradicts: "conflicts", neutral: "not confirmed" } as const;

export interface WebCheckView {
  headline: string;
  /** Detail line for insurer/operator; the citizen desk never shows it. */
  detail: string | null;
  verdict: string | null;
  links: { url: string; title: string }[];
  retrievedAt: string | null;
}

/** Pure: the Web check row. `null` run data -> the honest empty state. */
export function webCheckView(web: WebContext | null): WebCheckView {
  if (!web) return { headline: "No web check in the run shown.", detail: null, verdict: null, links: [], retrievedAt: null };
  const verdict = web.web_check ? VERDICT_WORD[web.web_check.verdict] : null;
  const headline =
    web.status === "unavailable"
      ? "The web search was not available for this run."
      : web.status === "empty"
        ? "The web search found nothing for this run."
        : verdict
          ? `A web search ${verdict === "confirmed" ? "confirmed" : verdict === "conflicts" ? "conflicts with" : "did not confirm"} the main statement.`
          : "A web search ran for this run.";
  const lat = web.latency_ms > 0 ? `${web.latency_ms} ms` : "latency n/a";
  return {
    headline,
    detail: `${web.status} · ${web.n_results} ${web.n_results === 1 ? "result" : "results"} · ${lat}${web.cached ? " · cached" : ""}`,
    verdict,
    links: web.results.slice(0, 3).map((r) => ({ url: r.url, title: r.title })),
    retrievedAt: web.retrieved_at ?? null,
  };
}
