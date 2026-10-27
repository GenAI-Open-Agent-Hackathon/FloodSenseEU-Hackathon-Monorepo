import { runModelLine } from "./modelChip";

/**
 * The Approvals queue: runs waiting for a person, newest first. Built only from what the API returns
 * (GET /runs/past rows and the live-run handoff id), never invented. A run the agents are still working on
 * is listed so a reviewer can see it coming, but it cannot be decided until it reaches awaiting_approval.
 */
export type QueueState = "awaiting" | "running" | "decided" | "other";

export interface QueueRow {
  runId: string;
  state: QueueState;
  /** Raw run status from the agents (awaiting_approval, running, approved, ...). */
  status: string;
  question: string | null;
  /** ISO start time from the run's own trace (past row created_at). */
  createdAt: string | null;
  eventId: string | null;
  lane: string | null;
  judgeOverall: number | null;
  /** True when the row came only from the handoff id (the past list did not carry it yet). */
  handoffOnly: boolean;
}

const rec = (v: unknown): Record<string, unknown> | null => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null);
const str = (v: unknown): string | null => (typeof v === "string" && v.trim().length > 0 ? v.trim() : null);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export function queueState(status: string | null, approval: string | null = null): QueueState {
  if (status === "awaiting_approval") return "awaiting";
  if (status === "running") return "running";
  if (approval === "approved" || approval === "edited" || approval === "rejected") return "decided";
  if (status === "approved" || status === "rejected" || status === "answered") return "decided";
  return "other";
}

/** Pure: GET /runs/past ({runs: [...]} or a bare list) as queue rows. Malformed rows are dropped. */
export function adoptPastRuns(body: unknown): QueueRow[] {
  const list = Array.isArray(body) ? body : Array.isArray(rec(body)?.runs) ? (rec(body)!.runs as unknown[]) : [];
  return list.flatMap((raw) => {
    const r = rec(raw);
    const runId = r && str(r.run_id);
    if (!r || !runId) return [];
    const status = str(r.status) ?? "unknown";
    return [
      {
        runId,
        state: queueState(status, str(r.approval)),
        status,
        question: str(r.question),
        createdAt: str(r.created_at),
        eventId: str(r.event_id),
        lane: str(r.lane),
        judgeOverall: num(r.judge_overall),
        handoffOnly: false,
      },
    ];
  });
}

/** A run this browser started (Alerts "Ask the agents to assess", or the Ask chat handoff). */
export interface StartedRun {
  runId: string;
  question: string;
  startedAt: string;
  eventId?: string | null;
}

const t = (iso: string | null): number => {
  const v = iso ? Date.parse(iso) : NaN;
  return Number.isFinite(v) ? v : -Infinity;
};

/**
 * Pure: the queue shown in the left pane. Awaiting runs first, then runs the agents are still working on, each
 * newest first. The handoff id (the newest live run that reached review in this tab) is kept even before
 * /runs/past lists it; runs started here are kept as "running" until the past list says otherwise.
 */
export function buildQueue(past: readonly QueueRow[], handoffRunId: string | null, started: readonly StartedRun[] = []): QueueRow[] {
  const byId = new Map<string, QueueRow>();
  for (const row of past) if (!byId.has(row.runId)) byId.set(row.runId, row);
  for (const s of started) {
    if (byId.has(s.runId)) continue;
    byId.set(s.runId, {
      runId: s.runId,
      state: "running",
      status: "running",
      question: s.question,
      createdAt: s.startedAt,
      eventId: s.eventId ?? null,
      lane: null,
      judgeOverall: null,
      handoffOnly: true,
    });
  }
  if (handoffRunId && !byId.has(handoffRunId)) {
    byId.set(handoffRunId, {
      runId: handoffRunId,
      state: "awaiting",
      status: "awaiting_approval",
      question: null,
      createdAt: null,
      eventId: null,
      lane: null,
      judgeOverall: null,
      handoffOnly: true,
    });
  }
  const rank: Record<QueueState, number> = { awaiting: 0, running: 1, decided: 2, other: 3 };
  return [...byId.values()]
    .filter((r) => r.state === "awaiting" || r.state === "running")
    .sort((a, b) => rank[a.state] - rank[b.state] || t(b.createdAt) - t(a.createdAt) || a.runId.localeCompare(b.runId));
}

/**
 * Pure: which run the right pane shows. The current pick while it is still awaiting; else the handoff run;
 * else the newest awaiting run; else null (the right pane shows the packed example, labelled as such).
 */
export function pickSelection(queue: readonly QueueRow[], current: string | null, handoff: string | null): string | null {
  const awaiting = queue.filter((r) => r.state === "awaiting");
  if (current && awaiting.some((r) => r.runId === current)) return current;
  if (handoff && awaiting.some((r) => r.runId === handoff)) return handoff;
  return awaiting[0]?.runId ?? null;
}

/** "27 Oct 2026, 11:42 UTC", or null. */
export function utcStamp(iso: string | null | undefined): string | null {
  const v = iso ? Date.parse(iso) : NaN;
  if (!Number.isFinite(v)) return null;
  const d = new Date(v);
  const day = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${day}, ${hh}:${mm} UTC`;
}

export interface HeaderFact {
  label: string;
  value: string;
}

export interface ApprovalHeader {
  /** "Live run 3f2a…" or "Packed example run …". */
  title: string;
  /** Live: the run's own facts. Example: a plain "not live" note. */
  kind: "live" | "example";
  facts: HeaderFact[];
  /** One line under the facts, e.g. why a fact is missing. */
  note: string | null;
}

const LANE_TEXT: Record<string, string> = { full: "Full investigation", quick: "Quick check" };

/**
 * Pure: the page header for the selected run. It states the run's own facts (id, start, lane, model, Judge)
 * and nothing about the console's fixture answer, so no "cached at" line from elsewhere leaks in.
 */
export function approvalHeader(input: {
  runId: string | null;
  row: QueueRow | null;
  modelIds: readonly string[];
  judgeScore: number | null;
  judgePasses: boolean | null;
  eventId?: string | null;
  /** The packed example's own run id, when no live run is selected. */
  exampleRunId?: string | null;
}): ApprovalHeader {
  const judge =
    input.judgeScore === null
      ? "not scored"
      : `${input.judgeScore.toFixed(2)}${input.judgePasses === null ? "" : input.judgePasses ? " · passes" : " · does not pass"}`;
  if (!input.runId) {
    return {
      title: "Packed example run",
      kind: "example",
      facts: [
        { label: "Run", value: input.exampleRunId ? `${input.exampleRunId} (example)` : "example" },
        { label: "Judge", value: judge },
      ],
      note: "No live run is waiting. This is the example shipped with the UI: a recording, not live, decided in this browser only.",
    };
  }
  const started = utcStamp(input.row?.createdAt);
  const lane = input.row?.lane ? (LANE_TEXT[input.row.lane] ?? input.row.lane) : null;
  const model = runModelLine(input.modelIds);
  const eventId = input.eventId ?? input.row?.eventId ?? null;
  const facts: HeaderFact[] = [
    { label: "Live run", value: input.runId },
    { label: "Started", value: started ?? "not reported" },
    { label: "Lane", value: lane ?? "not reported" },
    { label: "Model", value: model ?? "rules only (no model call recorded)" },
    { label: "Judge", value: judge },
  ];
  if (eventId) facts.push({ label: "Event", value: eventId });
  const missing = [!started && "start time", !lane && "lane"].filter(Boolean);
  return {
    title: `Live run ${input.runId}`,
    kind: "live",
    facts,
    note: missing.length ? `The run list did not report the ${missing.join(" or ")} for this run yet.` : null,
  };
}

/** Pure: the left-pane row's secondary line. */
export function queueRowLine(row: QueueRow): string {
  const when = utcStamp(row.createdAt);
  const state = row.state === "running" ? "Agents working" : "Awaiting your decision";
  return [state, when, row.eventId].filter(Boolean).join(" · ");
}
