import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, it } from "node:test";
import { FloodsenseEngines, InputError } from "../src/floodsense.ts";

const T0 = Date.parse("2024-10-29T17:25:00Z");
const clock = () => T0;

const approvedRun = {
  runId: "run-1725",
  request: "Why is Paiporta at risk this evening?",
  approval: { decision: "approved" as const, by: "analyst@insurer" },
  claims: [
    {
      text: "Poyo ravine discharge passed 100 m3/s at 17:25, upstream of Paiporta.",
      confidence: 0.9,
      citations: [{ queryId: "q-discharge-1725", view: "floodsense.discharge_daily" }],
      entities: ["Barranco del Poyo", "Paiporta"],
    },
    { text: "  " },
  ],
};

describe("H-MEM write-on-approval", () => {
  it("rejected runs write nothing", () => {
    const e = new FloodsenseEngines({ clock });
    const out = e.storeRun({ ...approvedRun, approval: { decision: "rejected", by: "analyst" } });
    assert.deepEqual(out.stored, []);
    assert.equal(out.skipped, 2);
    assert.equal(e.hmem.store.all().length, 0);
  });

  it("approved claims become long-term memories with Zetaris provenance and a ledger create", () => {
    const e = new FloodsenseEngines({ clock });
    const out = e.storeRun(approvedRun);
    assert.equal(out.stored.length, 1);
    assert.equal(out.skipped, 1);
    const record = e.hmem.store.get(out.stored[0])!;
    assert.equal(record.layer, "long_term");
    assert.equal(record.source, "floodsense:run:run-1725");
    assert.deepEqual(record.provenance.refs, ["zetaris:queryId:q-discharge-1725"]);
    assert.ok(record.tags.includes("entity:Paiporta"));
    assert.equal(e.ledger(record.id)[0].action, "create");
  });

  it("recall finds a remembered claim and feedback moves its confidence", () => {
    const e = new FloodsenseEngines({ clock });
    const [id] = e.storeRun(approvedRun).stored;
    const recalled = e.recall("Poyo ravine discharge upstream of Paiporta", { threshold: 0 });
    assert.equal(recalled.memories[0].id, id);
    assert.deepEqual(recalled.memories[0].provenance.refs, ["zetaris:queryId:q-discharge-1725"]);
    const after = e.feedback(id, "wrong");
    assert.ok(after.confidence < 0.9);
    assert.deepEqual(
      e.ledger(id).map((l) => l.action).filter((a) => a !== "read"),
      ["create", "feedback"],
    );
  });

  it("validates input", () => {
    const e = new FloodsenseEngines({ clock });
    assert.throws(() => e.storeRun({ ...approvedRun, approval: { decision: "maybe" as never, by: "x" } }), InputError);
    assert.throws(() => e.recall(""), InputError);
    assert.throws(() => e.feedback("mem-404", "helpful"), InputError);
    assert.throws(() => e.feedback("mem-1", "great" as never), InputError);
  });
});

describe("World Model hypothesis board", () => {
  const base = {
    runId: "run-1725",
    at: "2024-10-29T17:25:00Z",
    hypotheses: [
      {
        id: "h1",
        text: "Rain over the Poyo catchment drives the discharge spike",
        status: "proposed" as const,
        confidence: 0.6,
        concerns: [{ type: "river", name: "Barranco del Poyo" }],
        evidence: ["q-rain-1700"],
      },
    ],
  };

  it("records status changes as facts and keeps the latest on the board", async () => {
    const e = new FloodsenseEngines({ clock });
    let board = await e.upsertHypotheses(base);
    assert.equal(board.length, 1);
    assert.equal(board[0].status, "proposed");
    assert.deepEqual(board[0].concerns, ["Barranco del Poyo"]);
    board = await e.upsertHypotheses({
      ...base,
      at: "2024-10-29T17:40:00Z",
      hypotheses: [{ ...base.hypotheses[0], status: "supported", confidence: 0.85 }],
    });
    assert.equal(board[0].status, "supported");
    assert.equal(board[0].confidence, 0.85);
    assert.equal(e.board("another-run").length, 0);
  });

  it("re-ingesting the same observations changes nothing", async () => {
    const e = new FloodsenseEngines({ clock });
    const obs = [
      {
        externalId: "glofas:poyo:2024-10-29T17:00",
        type: "reading",
        title: "Poyo discharge 208 m3/s",
        at: "2024-10-29T17:00:00Z",
        source: { kind: "api", by: "zetaris", at: "2024-10-29T17:00:00Z" },
        entities: [{ type: "river", name: "Barranco del Poyo" }],
      },
    ];
    const first = await e.observe(obs);
    const second = await e.observe(obs);
    assert.equal(first.changed, true);
    assert.equal(second.changed, false);
  });

  it("rejects bad hypotheses", async () => {
    const e = new FloodsenseEngines({ clock });
    await assert.rejects(e.upsertHypotheses({ ...base, at: "not a date" }), InputError);
    await assert.rejects(
      e.upsertHypotheses({ ...base, hypotheses: [{ ...base.hypotheses[0], status: "maybe" as never }] }),
      InputError,
    );
  });
});

describe("persistence", () => {
  it("memories, ledger and board survive a restart", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "engines-"));
    try {
      const first = new FloodsenseEngines({ dataDir: dir, clock });
      const [id] = first.storeRun(approvedRun).stored;
      // Same timestamp twice: the later write wins, before and after the restart.
      for (const status of ["proposed", "refuted"] as const) {
        await first.upsertHypotheses({
          runId: "run-1725",
          at: "2024-10-29T17:25:00Z",
          hypotheses: [{ id: "h1", text: "Rain drives the spike", status }],
        });
      }
      assert.equal(first.board("run-1725")[0].status, "refuted");
      const second = new FloodsenseEngines({ dataDir: dir, clock });
      assert.equal(second.hmem.store.get(id)?.content, approvedRun.claims[0].text);
      assert.equal(second.ledger(id)[0].action, "create");
      assert.equal(second.board("run-1725")[0].status, "refuted");
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
