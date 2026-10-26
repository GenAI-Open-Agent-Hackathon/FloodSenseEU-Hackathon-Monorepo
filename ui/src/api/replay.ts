import { apiBaseUrl, apiTimeoutMs } from "./config";

/** One citation from a recorded run. Layer (c) carries a document passage. */
export interface ReplayCitation {
  id: string;
  layer: string;
  title: string;
  publisher: string | null;
  licence: string | null;
  quote: string | null;
  page: number | null;
  queryId: string | null;
}

export interface ReplayClaim {
  id: string;
  text: string;
  citations: ReplayCitation[];
}

export interface ReplayStep {
  seq: number;
  node: string;
  summary: string;
}

/** A recorded agent run, read from GET /runs/{id}/replay. Always a replay, never live. */
export interface RecordedRun {
  runId: string;
  label: string;
  summary: string;
  claims: ReplayClaim[];
  judgeOverall: number | null;
  judgePasses: boolean | null;
  trace: ReplayStep[];
}

const str = (value: unknown): string | null => (typeof value === "string" && value.length > 0 ? value : null);
const num = (value: unknown): number | null => (typeof value === "number" && Number.isFinite(value) ? value : null);
const rec = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;

function asCitation(value: unknown): ReplayCitation | null {
  const c = rec(value);
  const title = c && str(c.title);
  if (!c || !title) return null;
  return {
    id: str(c.citation_id) ?? title,
    layer: str(c.layer) ?? "?",
    title,
    publisher: str(c.publisher),
    licence: str(c.licence),
    quote: str(c.quote),
    page: num(rec(c.locator)?.page),
    queryId: str(c.query_id),
  };
}

/**
 * Pure adapter: the replay body, or null when it is not a usable recorded run.
 * A body the API serves as live is refused, so the popup never shows it as a replay by mistake.
 */
export function adoptReplay(body: unknown, runId: string): RecordedRun | null {
  const run = rec(body);
  if (!run || run.served_from !== "replay") return null;
  const summary = str(run.summary);
  if (!summary || !Array.isArray(run.claims)) return null;
  const claims: ReplayClaim[] = [];
  for (const raw of run.claims) {
    const claim = rec(raw);
    const text = claim && str(claim.text);
    if (!claim || !text) continue;
    const citations = Array.isArray(claim.citations)
      ? claim.citations.map(asCitation).filter((c): c is ReplayCitation => c !== null)
      : [];
    claims.push({ id: str(claim.claim_id) ?? text, text, citations });
  }
  const judge = rec(run.judge_summary);
  const trace: ReplayStep[] = Array.isArray(run.trace)
    ? run.trace.flatMap((raw) => {
        const step = rec(raw);
        const node = step && str(step.node);
        return step && node ? [{ seq: num(step.seq) ?? 0, node, summary: str(step.summary) ?? "" }] : [];
      })
    : [];
  const id = str(run.run_id) ?? runId;
  return {
    runId: id,
    label: str(rec(run.label)?.text) ?? `Replay of recorded run ${id} · not live`,
    summary,
    claims,
    judgeOverall: num(judge?.overall),
    judgePasses: typeof judge?.passes === "boolean" ? judge.passes : null,
    trace,
  };
}

/** VITE_REPLAY_RUN_ID, or null when unset. */
export function replayRunId(): string | null {
  return import.meta.env.VITE_REPLAY_RUN_ID?.trim() || null;
}

/** Fetch the recorded run. Any failure returns null, and the caller keeps the fixture answer. */
export async function fetchRecordedRun(runId: string, base = apiBaseUrl()): Promise<RecordedRun | null> {
  try {
    const response = await fetch(`${base}/runs/${encodeURIComponent(runId)}/replay`, {
      credentials: "omit",
      signal: AbortSignal.timeout(Math.max(apiTimeoutMs(), 5000)),
    });
    if (!response.ok) return null;
    return adoptReplay(await response.json(), runId);
  } catch {
    return null;
  }
}
