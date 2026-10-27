import { apiBaseUrl } from "./config";
import { buildRunRequest, mapRunResponse, runBadge, type AskInput } from "./ask";

/** Badge for a finished turn. Anything the API did not run live (cache hit, replay) is labelled so. */
export function turnBadge(run: RecordedRun): string {
  return run.servedFrom === "live" ? runBadge(run) : "Recorded/cached · not live";
}
import { adoptRunBody, type RecordedRun } from "./replay";
import { retryAfterSeconds, type LiveEvent } from "../lib/liveRun";
import { errorDetail } from "../lib/hitl";

export type StartResult =
  | { kind: "started"; runId: string; threadId: string | null }
  | { kind: "run"; run: RecordedRun }
  | { kind: "reply"; answer: string; suggestions: string[] }
  | { kind: "rate_limited"; retryAfterS: number | null; message: string }
  | { kind: "error"; message: string }
  | { kind: "aborted" };

const rec = (v: unknown): Record<string, unknown> | null => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null);

function suggestionsOf(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((s): s is string => typeof s === "string" && s.trim().length > 0).slice(0, 4) : [];
}

/** Pure: classify a POST /runs?wait=false answer. 202 starts a live run; 200 is a cache hit, a replay, or an intent reply. */
export function classifyStart(status: number, body: unknown, retryAfter: string | null): StartResult {
  const r = rec(body);
  if (status === 429) {
    const secs = retryAfterSeconds(retryAfter);
    return { kind: "rate_limited", retryAfterS: secs, message: "Too many questions right now." };
  }
  if (status >= 200 && status < 300 && r && r.kind === "reply" && typeof r.answer === "string" && !r.run_id) {
    return { kind: "reply", answer: r.answer, suggestions: suggestionsOf(r.suggestions) };
  }
  if (status === 202) {
    const runId = r && typeof r.run_id === "string" ? r.run_id : null;
    if (!runId) return { kind: "error", message: "The run started without a run id." };
    return { kind: "started", runId, threadId: typeof r?.thread_id === "string" ? r.thread_id : null };
  }
  const mapped = mapRunResponse(status, body, retryAfter);
  // feat/chat-front-door maps a reply to {ok:false, kind:"reply", reply:{answer, suggestions}}. Not an error.
  const loose = mapped as unknown as { kind?: unknown; message?: unknown; reply?: { answer?: unknown; suggestions?: unknown } };
  if (loose.kind === "reply") {
    const answer = typeof loose.reply?.answer === "string" ? loose.reply.answer : typeof loose.message === "string" ? loose.message : "";
    if (answer) return { kind: "reply", answer, suggestions: suggestionsOf(loose.reply?.suggestions) };
  }
  return mapped.ok ? { kind: "run", run: mapped.run } : { kind: "error", message: mapped.message };
}

export async function startLiveRun(input: AskInput, signal?: AbortSignal, base = apiBaseUrl()): Promise<StartResult> {
  let response: Response;
  try {
    response = await fetch(`${base}/runs?wait=false`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildRunRequest(input)),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) return { kind: "aborted" };
    return { kind: "error", message: `Could not reach the API (${(error as Error)?.message ?? "network error"}).` };
  }
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return classifyStart(response.status, body, response.headers.get("Retry-After"));
}

/** GET /runs/{id}: the raw body and the adopted run (null while it has no summary yet). */
export async function fetchRunSnapshot(
  runId: string,
  signal?: AbortSignal,
  base = apiBaseUrl(),
): Promise<{ status: number; body: Record<string, unknown> | null; run: RecordedRun | null }> {
  const response = await fetch(`${base}/runs/${encodeURIComponent(runId)}`, { credentials: "omit", signal });
  let body: Record<string, unknown> | null = null;
  try {
    body = rec(await response.json());
  } catch {
    body = null;
  }
  return { status: response.status, body, run: body ? adoptRunBody(body, runId) : null };
}

/**
 * Subscribe to GET /runs/{id}/events. If the stream breaks, poll GET /runs/{id} every 3 s instead,
 * feeding its trace through the same reducer (duplicates are dropped by seq). Returns a stop function.
 */
export function subscribeRunEvents(runId: string, onEvent: (event: LiveEvent) => void, base = apiBaseUrl()): () => void {
  let stopped = false;
  let source: EventSource | null = null;
  let timer: number | undefined;
  const parse = (data: string): unknown => {
    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  };
  const finish = () => {
    stopped = true;
    source?.close();
    if (timer !== undefined) window.clearTimeout(timer);
  };
  const poll = async () => {
    if (stopped) return;
    try {
      const snap = await fetchRunSnapshot(runId);
      if (stopped) return;
      if (snap.status === 404) {
        onEvent({ type: "status", data: { run_id: runId, status: "not_found" } });
        return finish();
      }
      const trace = Array.isArray(snap.body?.trace) ? snap.body.trace : [];
      for (const step of trace) onEvent({ type: "trace", data: step });
      const status = typeof snap.body?.status === "string" ? snap.body.status : "running";
      if (status !== "running") {
        onEvent({ type: "status", data: { run_id: runId, status, served_from: snap.body?.served_from, cached_at: snap.body?.cached_at } });
        return finish();
      }
    } catch {
      /* keep polling */
    }
    if (!stopped) timer = window.setTimeout(() => void poll(), 3000);
  };
  if (typeof EventSource === "undefined") {
    void poll();
    return finish;
  }
  source = new EventSource(`${base}/runs/${encodeURIComponent(runId)}/events`);
  source.addEventListener("started", (e) => onEvent({ type: "started", data: parse((e as MessageEvent).data) }));
  source.addEventListener("trace", (e) => onEvent({ type: "trace", data: parse((e as MessageEvent).data) }));
  source.addEventListener("status", (e) => {
    onEvent({ type: "status", data: parse((e as MessageEvent).data) });
    finish();
  });
  source.addEventListener("error", () => {
    // Both the API's own `event: error` and a dropped connection land here. Fall back to polling.
    if (stopped) return;
    source?.close();
    source = null;
    void poll();
  });
  return finish;
}

/** GET /runs/{id}/approval. 409 when the run is no longer waiting. */
export async function fetchApproval(runId: string, base = apiBaseUrl()): Promise<{ status: number; body: Record<string, unknown> | null }> {
  const response = await fetch(`${base}/runs/${encodeURIComponent(runId)}/approval`, { credentials: "omit" });
  let body: Record<string, unknown> | null = null;
  try {
    body = rec(await response.json());
  } catch {
    body = null;
  }
  return { status: response.status, body };
}

export async function postApproval(
  runId: string,
  body: unknown,
  base = apiBaseUrl(),
): Promise<{ ok: true; body: Record<string, unknown> | null } | { ok: false; status: number; message: string }> {
  let response: Response;
  try {
    response = await fetch(`${base}/runs/${encodeURIComponent(runId)}/approval`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    return { ok: false, status: 0, message: `Could not reach the API (${(error as Error)?.message ?? "network error"}).` };
  }
  let parsed: unknown = null;
  try {
    parsed = await response.json();
  } catch {
    parsed = null;
  }
  if (response.ok) return { ok: true, body: rec(parsed) };
  const detail = errorDetail(parsed);
  if (response.status === 422) return { ok: false, status: 422, message: detail ?? "The decision was refused (422)." };
  if (response.status === 409) return { ok: false, status: 409, message: detail ?? "This run is no longer waiting for a decision." };
  return { ok: false, status: response.status, message: `Decision failed (${response.status})${detail ? `: ${detail}` : ""}.` };
}
