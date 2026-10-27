import { describe, expect, it } from "vitest";
import livePy from "../../../agents/floodsense_agents/live.py?raw";
import { CITIZEN_ADVICE } from "./safety";

describe("citizen safety guidance", () => {
  it("is verbatim the agents' CITIZEN_ADVICE, not new advice", () => {
    const block = /CITIZEN_ADVICE = \(\r?\n((?:\s*"[^"]*"\r?\n)+)\)/.exec(livePy)?.[1] ?? "";
    const joined = [...block.matchAll(/"([^"]*)"/g)].map((m) => m[1]).join("");
    expect(joined).toBe(CITIZEN_ADVICE);
  });
});
