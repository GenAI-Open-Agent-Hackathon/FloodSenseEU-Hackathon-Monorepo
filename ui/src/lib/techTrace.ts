import type { RecordedRun } from "../api/replay";
import type { MemoryUsed } from "./hitl";
import { formatLatency, parseBoard } from "./pipeline";

/**
 * "How this answer was made": four sponsor tiles derived only from fields the run snapshot already carries
 * (trace, claims[].citations, memory_used, judge_summary, lane, router_reason, model_ids). Nothing is invented:
 * a tile with no evidence says so, and Nightshift is never claimed for a run without a model call.
 */

export type TileId = "zetaris" | "nightshift" | "hmem" | "world";

export const GLOSSARY: Record<TileId, string> = {
  zetaris: "Zetaris: one SQL layer over every source.",
  nightshift: "Meterless Nightshift: the cloud that runs the Nemotron language models.",
  hmem: "Meterless H-MEM: remembers only findings an analyst approved.",
  world: "Meterless World Model: tracks which hypotheses the evidence still supports.",
};

export interface TileDetail {
  label: string;
  value: string;
}

export interface Tile {
  id: TileId;
  name: string;
  /** False when the lane did not use this sponsor tool (the tile is dimmed, never hidden). */
  used: boolean;
  headline: string;
  glossary: string;
  details: TileDetail[];
}

export interface TechTraceModel {
  /** "Router → quick lane (live level question about KÖLN)", or null when the run states no lane or reason. */
  routerLine: string | null;
  /** "Checked 1.00 · hallucination 0%", or null without a judge score. */
  judgeLine: string | null;
  tiles: Tile[];
}

/* ---------- Zetaris ---------- */

export interface ZetarisUse {
  queryIds: string[];
  views: string[];
  /** True when document passages (layer c) were hydrated through the Zetaris JDBC connection. */
  ragChunks: number;
  upstream: { title: string; publisher: string | null; url: string | null }[];
}

/** Pure: distinct query ids over layer a and c citations, the view names of layer a, the upstream sources of layer b. */
export function zetarisUse(run: Pick<RecordedRun, "claims">): ZetarisUse {
  const queryIds: string[] = [];
  const views: string[] = [];
  const upstream: ZetarisUse["upstream"] = [];
  const seenUp = new Set<string>();
  let ragChunks = 0;
  const seenChunks = new Set<string>();
  for (const claim of run.claims) {
    for (const c of claim.citations) {
      if ((c.layer === "a" || c.layer === "c") && c.queryId && !queryIds.includes(c.queryId)) queryIds.push(c.queryId);
      if (c.layer === "a" && /^floodsense/i.test(c.title) && !views.includes(c.title)) views.push(c.title);
      if (c.layer === "c") {
        const key = c.chunkId ?? `${c.title}|${c.page ?? ""}|${c.paragraph ?? ""}`;
        if (!seenChunks.has(key)) {
          seenChunks.add(key);
          ragChunks += 1;
        }
      }
      if (c.layer === "b" && !seenUp.has(c.title)) {
        seenUp.add(c.title);
        upstream.push({ title: c.title, publisher: c.publisher, url: c.sourceUrl ?? null });
      }
    }
  }
  return { queryIds, views, ragChunks, upstream };
}

const shortView = (v: string): string => v.replace(/^floodsense(_seed)?\./i, "");

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

function zetarisTile(run: RecordedRun): Tile {
  const z = zetarisUse(run);
  const viewNames = z.views.map(shortView);
  if (z.ragChunks > 0) viewNames.push("document chunks");
  const details: TileDetail[] = [];
  if (z.queryIds.length) details.push({ label: "Query ids", value: z.queryIds.join(", ") });
  if (z.views.length) details.push({ label: "Views", value: z.views.join(", ") });
  if (z.ragChunks > 0) details.push({ label: "Documents", value: `${plural(z.ragChunks, "passage")} hydrated through Zetaris JDBC` });
  if (z.upstream.length) {
    details.push({ label: "Upstream sources", value: z.upstream.map((u) => (u.publisher ? `${u.title} (${u.publisher})` : u.title)).join("; ") });
  }
  const headline = z.queryIds.length
    ? `${plural(z.queryIds.length, "query", "queries")} across ${viewNames.length ? viewNames.join(", ") : "Zetaris views"}`
    : "No Zetaris query cited";
  return { id: "zetaris", name: "Zetaris", used: z.queryIds.length > 0, headline, glossary: GLOSSARY.zetaris, details };
}

/* ---------- Meterless Nightshift ---------- */

export interface ModelUse {
  id: string;
  name: string;
  /** fast / deep, when a trace step that ran this model states it. */
  lanes: string[];
  calls: number;
  latencyMs: number;
}

/** Display name for a Nemotron id; the three Nightshift models by size, anything else as stored. */
export function modelDisplay(id: string): string {
  const m = /nemotron-([\d.]+)-(super-vl|lightning|ultra)-(\d+)b/i.exec(id);
  if (!m) return id.includes("/") ? id.slice(id.lastIndexOf("/") + 1) : id;
  const kind = m[2].toLowerCase() === "super-vl" ? "Super VL" : m[2][0].toUpperCase() + m[2].slice(1).toLowerCase();
  return `Nemotron ${m[1]} ${kind} ${m[3]}B`;
}

const llmIds = (modelId: string | null | undefined): string[] =>
  (modelId ?? "")
    .split(",")
    .map((m) => m.trim())
    .filter((m) => m && m !== "deterministic");

/** Pure: the models that answered, from the trace's model_id, lane and latency_ms (run.modelIds when the trace names none). */
export function modelUse(run: Pick<RecordedRun, "trace" | "modelIds">): { models: ModelUse[]; calls: number; latencyMs: number } {
  const byId = new Map<string, ModelUse>();
  let calls = 0;
  let latencyMs = 0;
  for (const step of run.trace) {
    const ids = llmIds(step.modelId);
    if (!ids.length) continue;
    calls += 1;
    latencyMs += step.latencyMs ?? 0;
    for (const id of ids) {
      const use = byId.get(id) ?? { id, name: modelDisplay(id), lanes: [], calls: 0, latencyMs: 0 };
      use.calls += 1;
      use.latencyMs += step.latencyMs ?? 0;
      const lane = (step.lane ?? "").toLowerCase();
      if ((lane === "fast" || lane === "deep") && !use.lanes.includes(lane)) use.lanes.push(lane);
      byId.set(id, use);
    }
  }
  if (!byId.size) {
    for (const id of run.modelIds.flatMap((m) => llmIds(m))) {
      if (!byId.has(id)) byId.set(id, { id, name: modelDisplay(id), lanes: [], calls: 0, latencyMs: 0 });
    }
  }
  return { models: [...byId.values()], calls, latencyMs };
}

function totalLatency(run: Pick<RecordedRun, "trace">): number {
  return run.trace.reduce((n, s) => n + (s.latencyMs ?? 0), 0);
}

function nightshiftTile(run: RecordedRun): Tile {
  const use = modelUse(run);
  if (!use.models.length) {
    const total = totalLatency(run);
    const took = total > 0 ? ` in ${formatLatency(total)}` : "";
    return {
      id: "nightshift",
      name: "Meterless Nightshift",
      used: false,
      headline: "No model call",
      glossary: GLOSSARY.nightshift,
      details: [
        {
          label: "Why",
          value: `No model call: answered deterministically from Zetaris data — the router chose the cheapest safe path${took}.`,
        },
      ],
    };
  }
  const headline =
    use.calls > 0
      ? `${use.models.map((m) => m.name.replace(/^Nemotron [\d.]+ /, "")).join(" + ")} · ${plural(use.calls, "call")}`
      : use.models.map((m) => m.name).join(" + ");
  const details: TileDetail[] = use.models.map((m) => ({
    label: m.name,
    value: [m.lanes.length ? `${m.lanes.join("/")} lane` : null, m.calls ? plural(m.calls, "call") : null, m.latencyMs > 0 ? formatLatency(m.latencyMs) : null]
      .filter(Boolean)
      .join(" · ") || "answered",
  }));
  if (use.calls > 0) details.push({ label: "Total model time", value: `${formatLatency(use.latencyMs)} over ${plural(use.calls, "model call")}` });
  return { id: "nightshift", name: "Meterless Nightshift", used: true, headline, glossary: GLOSSARY.nightshift, details };
}

/* ---------- H-MEM ---------- */

export const NO_MEMORY_MATCH = "No approved memory matched this question yet";

function memoryDetail(m: MemoryUsed): TileDetail {
  const origin = m.seeded ? "demo seed" : m.runId ? `approved run ${m.runId}` : "approved";
  const tail = m.seeded && m.runId ? ` · ${m.runId}` : "";
  return { label: m.memoryId, value: `${origin}${tail}` };
}

function hmemTile(run: RecordedRun): Tile {
  const memories = run.memoryUsed ?? [];
  const writes = run.status === "awaiting_approval";
  const details: TileDetail[] = memories.map(memoryDetail);
  if (writes) details.push({ label: "On approval", value: "this finding is written to H-MEM" });
  if (!memories.length) {
    return {
      id: "hmem",
      name: "Meterless H-MEM",
      used: false,
      headline: writes ? `${NO_MEMORY_MATCH} · + writes on approval` : NO_MEMORY_MATCH,
      glossary: GLOSSARY.hmem,
      details,
    };
  }
  const seeded = memories.filter((m) => m.seeded).length;
  const parts = [`${memories.length} recalled`];
  if (seeded) parts.push(seeded === memories.length ? "demo seed" : `${seeded} demo seed`);
  if (writes) parts.push("+ writes on approval");
  return { id: "hmem", name: "Meterless H-MEM", used: true, headline: parts.join(" · "), glossary: GLOSSARY.hmem, details };
}

/* ---------- World Model ---------- */

/** "not_supported" -> "not supported". */
export const verdictWord = (state: string): string => state.replace(/_/g, " ");

function worldTile(run: RecordedRun): Tile {
  let board = null as ReturnType<typeof parseBoard>;
  for (const step of run.trace) {
    if (step.node !== "world_model") continue;
    board = parseBoard(step.summary) ?? board;
  }
  if (!board) {
    return { id: "world", name: "Meterless World Model", used: false, headline: "Not used by this lane", glossary: GLOSSARY.world, details: [] };
  }
  const states = board.states;
  return {
    id: "world",
    name: "Meterless World Model",
    used: true,
    headline: states.map((s) => `${s.id} ${verdictWord(s.state)}`).join(", "),
    glossary: GLOSSARY.world,
    details: [
      ...states.map((s) => ({ label: s.id, value: verdictWord(s.state) })),
      { label: "Board", value: `after ${board.after}` },
    ],
  };
}

/* ---------- Router + Judge ---------- */

/** "chose quick: live level question about X" -> "live level question about X". */
function reasonText(reason: string | null | undefined): string | null {
  const t = (reason ?? "").trim();
  if (!t) return null;
  return t.replace(/^chose\s+\w+:\s*/i, "").replace(/\s*·?\s*escalated:.*$/i, "").trim() || null;
}

export function routerLine(run: Pick<RecordedRun, "lane" | "routerReason">): string | null {
  const reason = reasonText(run.routerReason);
  if (run.lane && reason) return `Router → ${run.lane} lane (${reason})`;
  if (run.lane) return `Router → ${run.lane} lane`;
  return reason ? `Router → ${reason}` : null;
}

export function judgeLine(run: Pick<RecordedRun, "judgeOverall" | "hallucinationRate">): string | null {
  if (run.judgeOverall === null || run.judgeOverall === undefined) return null;
  const halluc = run.hallucinationRate === null || run.hallucinationRate === undefined ? "" : ` · hallucination ${Math.round(run.hallucinationRate * 100)}%`;
  return `Checked ${run.judgeOverall.toFixed(2)}${halluc}`;
}

/** Pure: everything the TechTrace panel draws. */
export function buildTechTrace(run: RecordedRun): TechTraceModel {
  return {
    routerLine: routerLine(run),
    judgeLine: judgeLine(run),
    tiles: [zetarisTile(run), nightshiftTile(run), hmemTile(run), worldTile(run)],
  };
}
