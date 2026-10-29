import { describe, expect, it, vi } from "vitest";

describe("prefetchLiveWatch", () => {
  it("fires eu_watch, hazard_now and gauge_levels together, once each", async () => {
    const urls: string[] = [];
    vi.stubGlobal("fetch", (u: string) => {
      urls.push(String(u));
      return new Promise(() => undefined); // never settles: all three must start without waiting
    });
    const { prefetchLiveWatch } = await import("./useLiveWatch");
    prefetchLiveWatch();
    prefetchLiveWatch();
    expect(urls.filter((u) => u.endsWith("/views/eu_watch"))).toHaveLength(1);
    expect(urls.filter((u) => u.endsWith("/views/hazard_now"))).toHaveLength(1);
    expect(urls.filter((u) => u.endsWith("/views/gauge_levels"))).toHaveLength(1);
  });
});
