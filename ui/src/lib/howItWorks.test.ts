import { describe, expect, it } from "vitest";
import { boxStatuses, feedsMode, systemStatus } from "./howItWorks";

const config = {
  kind: "ok" as const,
  body: {
    flags: { FF_LIVE_DATA: false, FF_HMEM: true, FF_RAG_DOCS: true, FF_HITL: true, FF_JUDGE: true },
    lanes: { fast: "nvidia/nemotron-3.5-lightning-30b-a3b", deep: "nvidia/nemotron-3.5-lightning-30b-a3b" },
  },
};

describe("boxStatuses", () => {
  it("handles a missing /system (404) as unknown, not down", () => {
    const s = boxStatuses(config, { kind: "missing" });
    expect(s.agents).toBe("ok");
    expect(s.nightshift).toBe("ok");
    expect(s.memory).toBe("ok");
    expect(s.feeds).toBe("off");
    expect(s.redis).toBe("unknown");
    expect(s.zetaris).toBe("unknown");
  });

  it("reads /system components in several shapes", () => {
    const system = { kind: "ok" as const, body: { components: { redis: { status: "ok" }, zetaris: "down", pgvector: true } } };
    const s = boxStatuses(config, system);
    expect(s.redis).toBe("ok");
    expect(s.zetaris).toBe("down");
    expect(s.rag).toBe("ok");
    expect(systemStatus({ kind: "ok", body: { data: { services: { redis: { ok: false } } } } }, ["redis"])).toBe("down");
  });

  it("marks everything unreachable when the API is down", () => {
    const s = boxStatuses({ kind: "down" }, { kind: "down" });
    expect(s.agents).toBe("down");
    expect(s.router).toBe("down");
    expect(s.human).toBe("unknown");
  });

  it("names seed data or live feeds", () => {
    expect(feedsMode(config)).toBe("seed data");
    expect(feedsMode({ kind: "ok", body: { flags: { FF_LIVE_DATA: true } } })).toBe("live feeds");
    expect(feedsMode({ kind: "missing" })).toBeNull();
  });
});
