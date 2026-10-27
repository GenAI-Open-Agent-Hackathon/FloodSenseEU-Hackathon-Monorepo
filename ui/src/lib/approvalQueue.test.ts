import { describe, expect, it } from "vitest";
import { adoptPastRuns, approvalHeader, buildQueue, pickSelection, queueRowLine, utcStamp } from "./approvalQueue";

const PAST = {
  runs: [
    { run_id: "old", status: "awaiting_approval", question: "Old one", created_at: "2026-10-27T08:00:00Z", lane: "full", judge_overall: 0.8 },
    { run_id: "done", status: "approved", approval: "approved", created_at: "2026-10-27T11:00:00Z" },
    { run_id: "new", status: "awaiting_approval", question: "Kaub warning", created_at: "2026-10-27T10:30:00Z", lane: "full", event_id: "LIVE-EU" },
    { run_id: "busy", status: "running", question: "Still working", created_at: "2026-10-27T11:20:00Z" },
    { status: "awaiting_approval" },
  ],
};

describe("approval queue layout", () => {
  it("adopts /runs/past rows and drops malformed ones", () => {
    const rows = adoptPastRuns(PAST);
    expect(rows.map((r) => [r.runId, r.state])).toEqual([
      ["old", "awaiting"],
      ["done", "decided"],
      ["new", "awaiting"],
      ["busy", "running"],
    ]);
    expect(adoptPastRuns(null)).toEqual([]);
    expect(adoptPastRuns([{ run_id: "x", status: "running" }])).toHaveLength(1);
  });

  it("lists awaiting runs newest first, then running ones, never decided ones", () => {
    const queue = buildQueue(adoptPastRuns(PAST), null);
    expect(queue.map((r) => r.runId)).toEqual(["new", "old", "busy"]);
  });

  it("keeps the handoff run and runs started here before the past list has them", () => {
    const queue = buildQueue(adoptPastRuns(PAST), "handoff", [{ runId: "mine", question: "Assess Köln", startedAt: "2026-10-27T11:30:00Z" }]);
    expect(queue.map((r) => [r.runId, r.state])).toEqual([
      ["new", "awaiting"],
      ["old", "awaiting"],
      ["handoff", "awaiting"],
      ["mine", "running"],
      ["busy", "running"],
    ]);
    // A started run the past list already carries keeps the list's own status.
    const again = buildQueue(adoptPastRuns(PAST), null, [{ runId: "new", question: "x", startedAt: "2026-10-27T11:30:00Z" }]);
    expect(again.find((r) => r.runId === "new")?.state).toBe("awaiting");
  });

  it("selects the current pick, else the handoff, else the newest awaiting run, else nothing (the example)", () => {
    const queue = buildQueue(adoptPastRuns(PAST), "old");
    expect(pickSelection(queue, "new", "old")).toBe("new");
    expect(pickSelection(queue, null, "old")).toBe("old");
    expect(pickSelection(queue, "busy", null)).toBe("new");
    expect(pickSelection(queue, "gone", "gone")).toBe("new");
    expect(pickSelection([], null, null)).toBeNull();
  });

  it("writes the row line from the run's own state and time", () => {
    const [row] = buildQueue(adoptPastRuns(PAST), null);
    expect(queueRowLine(row)).toBe("Awaiting your decision · 27 Oct 2026, 10:30 UTC · LIVE-EU");
    expect(utcStamp("nonsense")).toBeNull();
  });
});

describe("Approvals header", () => {
  const [row] = buildQueue(adoptPastRuns(PAST), null);

  it("states the live run's own facts: id, start, lane, model, Judge", () => {
    const h = approvalHeader({
      runId: "new",
      row,
      modelIds: ["deterministic", "nvidia/nemotron-3.5-lightning-30b-a3b"],
      judgeScore: 0.91,
      judgePasses: true,
    });
    expect(h.kind).toBe("live");
    expect(h.title).toBe("Live run new");
    expect(h.facts).toEqual([
      { label: "Live run", value: "new" },
      { label: "Started", value: "27 Oct 2026, 10:30 UTC" },
      { label: "Lane", value: "Full investigation" },
      { label: "Model", value: "Nemotron 3.5 Lightning 30B via Nightshift" },
      { label: "Judge", value: "0.91 · passes" },
      { label: "Event", value: "LIVE-EU" },
    ]);
    expect(h.note).toBeNull();
    // No serving or cache line from the console's fixture answer leaks into a live run's header.
    expect(JSON.stringify(h)).not.toMatch(/cached at|replay|not live/i);
  });

  it("says what it does not know instead of inventing it", () => {
    const h = approvalHeader({ runId: "handoff", row: null, modelIds: [], judgeScore: null, judgePasses: null });
    expect(h.facts.find((f) => f.label === "Started")?.value).toBe("not reported");
    expect(h.facts.find((f) => f.label === "Model")?.value).toMatch(/rules only/);
    expect(h.facts.find((f) => f.label === "Judge")?.value).toBe("not scored");
    expect(h.note).toMatch(/start time or lane/);
  });

  it("labels the packed example as a recording, not live", () => {
    const h = approvalHeader({ runId: null, row: null, modelIds: [], judgeScore: 0.89, judgePasses: null, exampleRunId: "run_fixture" });
    expect(h.kind).toBe("example");
    expect(h.facts[0]).toEqual({ label: "Run", value: "run_fixture (example)" });
    expect(h.note).toMatch(/not live/);
  });
});
