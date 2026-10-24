// HTTP surface for the agents. JSON in, JSON out, snake_case, Node built-ins only.
//
//   GET  /health                       engine counts
//   POST /hmem/recall                  { query, top_n?, threshold? }
//   POST /hmem/store                   { run_id, question, event_id?, approval: { status, reviewer? }, claims: [...] }
//   POST /hmem/feedback                { memory_id, kind: helpful | not_helpful | wrong }
//   GET  /hmem/ledger?memory_id=...    trust-ledger trace for one memory
//   POST /wm/observations              { anomalies?: [...], observations?: [...] }  (idempotent ingest)
//   POST /wm/hypotheses                { run_id, at, by?, hypotheses: [...] }
//   GET  /wm/board?run_id=...          hypothesis board
//   GET  /wm/timeline?limit=...        latest World Model events
//
// Field names follow agents/floodsense_agents/models.py and contracts/; see README.md.

import http from "node:http";
import { FloodsenseEngines, InputError } from "./floodsense.ts";

const MAX_BODY_BYTES = 1_000_000;

export function createServer(engines: FloodsenseEngines): http.Server {
  return http.createServer((req, res) => {
    handle(engines, req, res).catch((err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      if (err instanceof InputError || err instanceof SyntaxError) {
        send(res, 400, { error: message });
      } else {
        console.error("engines: unexpected error:", message);
        send(res, 500, { error: "internal error" });
      }
    });
  });
}

async function handle(engines: FloodsenseEngines, req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
  const url = new URL(req.url ?? "/", "http://engines.local");
  const route = `${req.method} ${url.pathname}`;
  switch (route) {
    case "GET /health":
      return send(res, 200, { ok: true, ...engines.stats() });
    case "POST /hmem/recall": {
      const body = await readJson(req);
      return send(res, 200, engines.recall(body.query, { top_n: body.top_n, threshold: body.threshold }));
    }
    case "POST /hmem/store":
      return send(res, 200, engines.storeRun(await readJson(req)));
    case "POST /hmem/feedback": {
      const body = await readJson(req);
      return send(res, 200, engines.feedback(body.memory_id, body.kind));
    }
    case "GET /hmem/ledger":
      return send(res, 200, { entries: engines.ledger(url.searchParams.get("memory_id") ?? "") });
    case "POST /wm/observations":
      return send(res, 200, await engines.observe(await readJson(req)));
    case "POST /wm/hypotheses":
      return send(res, 200, { board: await engines.upsertHypotheses(await readJson(req)) });
    case "GET /wm/board":
      return send(res, 200, { board: engines.board(url.searchParams.get("run_id")) });
    case "GET /wm/timeline": {
      const raw = url.searchParams.get("limit");
      const limit = raw === null ? 100 : /^\d+$/.test(raw) ? Number(raw) : Number.NaN;
      return send(res, 200, { events: engines.timeline(limit) });
    }
    default:
      return send(res, 404, { error: `no route for ${route}` });
  }
}

async function readJson(req: http.IncomingMessage): Promise<any> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new InputError("request body is larger than 1 MB");
    chunks.push(chunk as Buffer);
  }
  const text = Buffer.concat(chunks).toString("utf-8");
  if (!text.trim()) throw new InputError("request body must be JSON");
  const value = JSON.parse(text);
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new InputError("request body must be a JSON object");
  }
  return value;
}

function send(res: http.ServerResponse, status: number, payload: unknown): void {
  const body = JSON.stringify(payload);
  res.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
  res.end(body);
}
