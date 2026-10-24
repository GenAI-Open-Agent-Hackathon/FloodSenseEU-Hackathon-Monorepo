// FloodSense adapter over the Meterless reference engines.
//
// H-MEM keeps what humans approved (write-on-approval) and recalls it for the
// next run, with a trust-ledger trace for every memory. World Model keeps the
// hypothesis board and the observations behind it as an append-only event log.
// The vendored engines under ../vendor are used unchanged; this file only maps
// FloodSense shapes onto their public APIs.

import fs from "node:fs";
import path from "node:path";
import { HMEM } from "../vendor/hmem/reference/src/index.ts";
import type { FeedbackKind, LedgerEntry, MemoryRecord } from "../vendor/hmem/reference/src/index.ts";
import { WorldModel } from "../vendor/world-model/reference/src/index.ts";
import type { Entity, IngestObservation, IngestReport, Provenance } from "../vendor/world-model/reference/src/index.ts";

export const NAMESPACE = "floodsense";
export const HYPOTHESIS_STATUSES = ["proposed", "supported", "refuted", "revised"] as const;
export type HypothesisStatus = (typeof HYPOTHESIS_STATUSES)[number];
export const APPROVAL_DECISIONS = ["approved", "edited", "rejected"] as const;
export type ApprovalDecision = (typeof APPROVAL_DECISIONS)[number];
const FEEDBACK_KINDS: readonly FeedbackKind[] = ["helpful", "not_helpful", "wrong"];

export class InputError extends Error {}

export interface Citation {
  queryId: string;
  view?: string;
  sql?: string;
}

export interface ClaimInput {
  text: string;
  confidence?: number;
  citations?: Citation[];
  entities?: string[];
}

export interface StoreRunInput {
  runId: string;
  request: string;
  approval: { decision: ApprovalDecision; by: string };
  claims: ClaimInput[];
}

export interface RecalledMemory {
  id: string;
  content: string;
  relevance: number;
  confidence: number;
  source: string;
  layer: string;
  tags: string[];
  provenance: MemoryRecord["provenance"];
}

export interface HypothesisInput {
  id: string;
  text: string;
  status: HypothesisStatus;
  confidence?: number;
  concerns?: { type: string; name: string }[];
  evidence?: string[];
}

export interface HypothesesInput {
  runId: string;
  at: string;
  by?: string;
  hypotheses: HypothesisInput[];
}

export interface BoardItem {
  id: string;
  hypothesisId: string;
  text: string;
  status: string;
  confidence: number | null;
  evidence: string[];
  concerns: string[];
  updatedAt: string;
}

export interface EnginesOptions {
  /** Directory for JSON persistence. Omit to keep everything in memory. */
  dataDir?: string;
  /** Injectable clock for H-MEM and World Model operator actions. */
  clock?: () => number;
}

export class FloodsenseEngines {
  readonly hmem: HMEM;
  readonly world: WorldModel;

  constructor(opts: EnginesOptions = {}) {
    const clock = opts.clock ?? Date.now;
    let hmemDir: string | undefined;
    if (opts.dataDir) {
      hmemDir = path.join(opts.dataDir, "hmem");
      fs.mkdirSync(hmemDir, { recursive: true });
    }
    this.hmem = new HMEM({ clock, persistDir: hmemDir, actor: "floodsense" });
    this.world = new WorldModel({
      namespace: NAMESPACE,
      storage: opts.dataDir ? "local" : "memory",
      directory: opts.dataDir,
      clock: () => new Date(clock()),
    });
  }

  // ------------------------------------------------------------------ H-MEM

  /** Write-on-approval: approved or edited runs become memories; rejected runs write nothing. */
  storeRun(input: StoreRunInput): { stored: string[]; skipped: number; reason?: string } {
    requireText(input.runId, "runId");
    requireText(input.request, "request");
    if (!input.approval || !APPROVAL_DECISIONS.includes(input.approval.decision)) {
      throw new InputError(`approval.decision must be one of ${APPROVAL_DECISIONS.join(", ")}`);
    }
    requireText(input.approval.by, "approval.by");
    if (!Array.isArray(input.claims)) throw new InputError("claims must be a list");
    if (input.approval.decision === "rejected") {
      return { stored: [], skipped: input.claims.length, reason: "rejected runs are not remembered" };
    }
    const stored: string[] = [];
    let skipped = 0;
    for (const claim of input.claims) {
      if (!claim || typeof claim.text !== "string" || !claim.text.trim()) {
        skipped += 1;
        continue;
      }
      const queryIds = (claim.citations ?? []).map((c) => c?.queryId).filter((q): q is string => !!q);
      const entities = (claim.entities ?? []).filter((e) => typeof e === "string" && e.trim());
      const record = this.hmem.add({
        content: claim.text.trim(),
        type: "factual",
        layer: "long_term",
        confidence: claim.confidence ?? 0.8,
        source: `floodsense:run:${input.runId}`,
        missionId: input.runId,
        tags: ["floodsense", `run:${input.runId}`, ...entities.map((e) => `entity:${e}`)],
        provenance: {
          origin: "plan_completion",
          learnedAt: this.hmem.clock(),
          label: `run ${input.runId} ${input.approval.decision} by ${input.approval.by}`,
          refs: queryIds.map((q) => `zetaris:queryId:${q}`),
        },
      });
      stored.push(record.id);
    }
    return { stored, skipped };
  }

  recall(query: string, opts: { topN?: number; threshold?: number } = {}): {
    memories: RecalledMemory[];
    trace: unknown;
  } {
    requireText(query, "query");
    const result = this.hmem.query(query, { topN: opts.topN, threshold: opts.threshold });
    return {
      memories: result.memories.map(({ memory, relevance }) => ({
        id: memory.id,
        content: memory.content,
        relevance: Number(relevance.toFixed(4)),
        confidence: memory.confidence,
        source: memory.source,
        layer: memory.layer,
        tags: memory.tags,
        provenance: memory.provenance,
      })),
      trace: result.trace,
    };
  }

  feedback(memoryId: string, kind: FeedbackKind): { memoryId: string; confidence: number } {
    requireText(memoryId, "memoryId");
    if (!FEEDBACK_KINDS.includes(kind)) {
      throw new InputError(`kind must be one of ${FEEDBACK_KINDS.join(", ")}`);
    }
    if (!this.hmem.store.get(memoryId)) throw new InputError(`unknown memory ${memoryId}`);
    this.hmem.feedback(memoryId, kind);
    return { memoryId, confidence: this.hmem.store.get(memoryId)!.confidence };
  }

  /** The trust-ledger trace that answers "why does the agent remember this?". */
  ledger(memoryId: string): LedgerEntry[] {
    requireText(memoryId, "memoryId");
    return this.hmem.ledger.history(memoryId);
  }

  // ------------------------------------------------------------ World Model

  /** Readings, warnings and sources as idempotent observations (re-ingest is a no-op). */
  observe(observations: IngestObservation[]): Promise<IngestReport> {
    if (!Array.isArray(observations) || observations.length === 0) {
      throw new InputError("observations must be a non-empty list");
    }
    for (const o of observations) {
      requireText(o?.externalId, "observation.externalId");
      requireText(o?.title, "observation.title");
      requireText(o?.at, "observation.at");
      if (!o.source?.kind) throw new InputError("observation.source.kind is required");
    }
    return this.world.ingest(observations);
  }

  /** Upsert hypotheses for a run and record each status change as a fact. */
  async upsertHypotheses(input: HypothesesInput): Promise<BoardItem[]> {
    requireText(input.runId, "runId");
    requireText(input.at, "at");
    if (Number.isNaN(Date.parse(input.at))) throw new InputError("at must be an ISO timestamp");
    if (!Array.isArray(input.hypotheses) || input.hypotheses.length === 0) {
      throw new InputError("hypotheses must be a non-empty list");
    }
    for (const h of input.hypotheses) {
      requireText(h?.id, "hypothesis.id");
      requireText(h?.text, "hypothesis.text");
      if (!HYPOTHESIS_STATUSES.includes(h.status)) {
        throw new InputError(`hypothesis.status must be one of ${HYPOTHESIS_STATUSES.join(", ")}`);
      }
    }
    const source: Provenance = { kind: "agent", by: input.by ?? "floodsense-agents", at: input.at, runId: input.runId };
    for (const h of input.hypotheses) {
      const entity = await this.world.upsertEntity({
        type: "hypothesis",
        externalKey: { system: "floodsense", id: `${input.runId}:${h.id}` },
        attrs: { runId: input.runId, hypothesisId: h.id, text: h.text, evidence: h.evidence ?? [] },
        source,
      });
      await this.world.assertFact({
        about: entity.id,
        predicate: "status",
        value: h.status,
        confidence: h.confidence ?? 0.5,
        source,
      });
      for (const c of h.concerns ?? []) {
        if (!c?.type || !c?.name) continue;
        const target = await this.world.upsertEntity({ type: c.type, name: c.name, source });
        await this.world.relate({ from: entity.id, type: "concerns", to: target.id, validFrom: input.at, source });
      }
    }
    return this.board(input.runId);
  }

  board(runId?: string): BoardItem[] {
    const graph = this.world.view("graph");
    const facts = this.world.view("facts");
    // The reference sets supersededBy and entity attrs in memory only, so a
    // reload replays the facts without saying which is current. Re-derive it
    // from the log with the engine's own default policy (most-recent-wins:
    // later assertedAt wins, and a tie goes to the later write).
    const seqOf = new Map<string, number>();
    for (const ev of this.world.events()) {
      if (ev.kind === "assertFact") seqOf.set((ev.payload as { id: string }).id, ev.seq);
    }
    const hypotheses = graph.query({
      type: "hypothesis",
      where: (e: Entity) => runId === undefined || e.attrs.runId === runId,
    });
    return hypotheses
      .map((e) => {
        const current = facts
          .about(e.id)
          .filter((f) => f.predicate === "status")
          .sort((a, b) => b.assertedAt.localeCompare(a.assertedAt) || (seqOf.get(b.id) ?? 0) - (seqOf.get(a.id) ?? 0))[0];
        return {
          id: e.id,
          hypothesisId: String(e.attrs.hypothesisId ?? ""),
          text: String(e.attrs.text ?? ""),
          status: current ? String(current.value) : "proposed",
          confidence: current ? current.confidence : null,
          evidence: Array.isArray(e.attrs.evidence) ? (e.attrs.evidence as string[]) : [],
          concerns: graph.neighborsOf(e.id, { via: "concerns" }).map((n) => n.name ?? n.id),
          updatedAt: e.updatedAt,
        };
      })
      .sort((a, b) => a.hypothesisId.localeCompare(b.hypothesisId));
  }

  timeline(limit = 100): { seq: number; kind: string; at: string; id: string }[] {
    const events = this.world.events();
    return events.slice(Math.max(0, events.length - limit)).map((e) => ({ seq: e.seq, kind: e.kind, at: e.at, id: e.id }));
  }

  stats(): Record<string, unknown> {
    return {
      hmem: { memories: this.hmem.store.all().length, ledgerEntries: this.hmem.ledger.all().length },
      worldModel: {
        events: this.world.events().length,
        hypotheses: this.world.view("graph").query({ type: "hypothesis" }).length,
      },
    };
  }
}

function requireText(value: unknown, name: string): void {
  if (typeof value !== "string" || !value.trim()) throw new InputError(`${name} is required`);
}
