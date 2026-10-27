import { describe, expect, it } from "vitest";
import { classifyError, friendlyError, statusFromMessage, stripInternal } from "./friendlyError";

const RAW = "The service failed (503): agents service unreachable at http://agents:8100: RemoteProtocolError.";

describe("stripInternal", () => {
  it("removes URLs and host:port pairs", () => {
    const out = stripInternal(RAW);
    expect(out).not.toMatch(/agents:8100|http/);
    expect(out).toMatch(/RemoteProtocolError/);
    expect(stripInternal("GET http://localhost:18000/runs/x failed; 10.0.0.5:8000 down; redis:6379")).not.toMatch(/localhost|10\.0\.0\.5|6379/);
  });
});

describe("friendlyError", () => {
  it("503 / unreachable: agents restarting, retry, offer recorded", () => {
    expect(statusFromMessage(RAW)).toBe(503);
    const f = friendlyError(503, RAW, "insurer");
    expect(f).toMatchObject({ kind: "unavailable", retry: true, offerRecorded: true });
    expect(f.text).toMatch(/^Our agents are restarting or busy right now/);
    expect(f.text).not.toMatch(/503|http/);
    expect(f.technical).not.toMatch(/agents:8100/);
    expect(friendlyError(null, "Could not reach the API (Failed to fetch).").kind).toBe("unavailable");
    expect(friendlyError(502, "x", "citizen").text).toMatch(/local authorities/);
  });
  it("timeouts", () => {
    expect(friendlyError(504, "gateway").text).toMatch(/^This is taking longer than usual/);
    expect(classifyError(null, "Lost contact with run r1 for over 60 s")).toBe("timeout");
  });
  it("422: rephrase, no retry", () => {
    expect(friendlyError(422, "Request refused: bad")).toMatchObject({ text: "I couldn't read that question — try rephrasing.", retry: false });
  });
  it("failed and not found", () => {
    expect(classifyError(null, "Run r1 failed after it started.")).toBe("failed");
    expect(classifyError(null, "Run r1 was not found.")).toBe("not_found");
  });
});
