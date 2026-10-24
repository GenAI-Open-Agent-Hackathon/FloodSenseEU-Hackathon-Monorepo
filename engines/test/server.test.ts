import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { after, before, describe, it } from "node:test";
import { FloodsenseEngines } from "../src/floodsense.ts";
import { createServer } from "../src/server.ts";

const server = createServer(new FloodsenseEngines({ clock: () => Date.parse("2024-10-29T17:25:00Z") }));
let base = "";

before(async () => {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
after(() => new Promise<void>((resolve) => server.close(() => resolve())));

async function call(method: string, path: string, body?: unknown): Promise<{ status: number; json: any }> {
  const res = await fetch(base + path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
  return { status: res.status, json: await res.json() };
}

describe("engines HTTP", () => {
  it("health reports both engines", async () => {
    const { status, json } = await call("GET", "/health");
    assert.equal(status, 200);
    assert.equal(json.ok, true);
    assert.ok("hmem" in json && "worldModel" in json);
  });

  it("store, recall, ledger round trip", async () => {
    const stored = await call("POST", "/hmem/store", {
      runId: "run-1",
      request: "Why Paiporta?",
      approval: { decision: "edited", by: "analyst" },
      claims: [{ text: "Paiporta sits on the Poyo ravine outflow.", citations: [{ queryId: "q-1" }] }],
    });
    assert.equal(stored.status, 200);
    const id = stored.json.stored[0];
    const recalled = await call("POST", "/hmem/recall", { query: "Paiporta Poyo ravine", threshold: 0 });
    assert.equal(recalled.json.memories[0].id, id);
    const ledger = await call("GET", `/hmem/ledger?memoryId=${id}`);
    assert.equal(ledger.json.entries[0].action, "create");
  });

  it("hypotheses and board", async () => {
    const res = await call("POST", "/wm/hypotheses", {
      runId: "run-1",
      at: "2024-10-29T17:25:00Z",
      hypotheses: [{ id: "h1", text: "Upstream rain", status: "proposed" }],
    });
    assert.equal(res.status, 200);
    assert.equal(res.json.board[0].status, "proposed");
    const board = await call("GET", "/wm/board?runId=run-1");
    assert.equal(board.json.board.length, 1);
    const timeline = await call("GET", "/wm/timeline?limit=5");
    assert.ok(timeline.json.events.length > 0);
  });

  it("bad input is a 400 and unknown routes are a 404", async () => {
    assert.equal((await call("POST", "/hmem/recall", "{not json")).status, 400);
    assert.equal((await call("POST", "/hmem/recall", [1, 2])).status, 400);
    assert.equal((await call("POST", "/hmem/store", { runId: "x" })).status, 400);
    assert.equal((await call("GET", "/nope")).status, 404);
  });
});
