import { afterEach, describe, expect, it } from "vitest";
import { llmBoxTitle, providerLabel, setLlmBackend } from "./lanes";
import { modelChip, runModelLine } from "./modelChip";
import { asWatchEvent, plainEventText, RATE_LIMIT_TEXT } from "./controlTower";

const ID = "nvidia/nemotron-3.5-lightning-30b-a3b";
afterEach(() => setLlmBackend(null));

describe("backend-aware LLM wording", () => {
  it("names Nebius Token Factory when the backend is nebius", () => {
    setLlmBackend("nebius");
    expect(providerLabel(ID)).toBe("Nebius Token Factory");
    expect(modelChip(ID, "fast")).toBe("Nemotron 3.5 Lightning 30B · Nebius Token Factory fast lane");
    expect(runModelLine([ID])).toBe("Nemotron 3.5 Lightning 30B via Nebius Token Factory");
    expect(llmBoxTitle("nebius")).toBe("Nebius Token Factory · NVIDIA Nemotron");
  });
  it("keeps Nightshift when it is the backend or still unknown", () => {
    expect(runModelLine([ID])).toBe("Nemotron 3.5 Lightning 30B via Nightshift");
    setLlmBackend("nightshift");
    expect(modelChip(ID, "deep")).toBe("Nemotron 3.5 Lightning 30B · Nightshift deep lane");
    expect(llmBoxTitle("nightshift")).toBe("Nightshift · NVIDIA Nemotron");
    expect(llmBoxTitle(null)).toBe("Language model · NVIDIA Nemotron");
  });
  it("a stated provider wins over the backend", () => {
    setLlmBackend("nebius");
    expect(providerLabel(ID, "nightshift")).toBe("Nightshift");
  });
});

describe("raw upstream rate-limit text", () => {
  const raw =
    "Could not read hazard_now this scan... (Zetaris HTTP 400: ... HTTP response code: 429 for URL: https://flood-api.open-...)";
  it("becomes a plain sentence with the raw text as detail", () => {
    expect(plainEventText(raw)).toEqual({ text: RATE_LIMIT_TEXT, detail: raw });
    const e = asWatchEvent({ id: "w00000001", ts: "2026-10-30T10:00:00Z", kind: "info", agent: "Watch", tone: "neutral", text: raw, source: { view: "hazard_now" } });
    expect(e?.text).toBe(RATE_LIMIT_TEXT);
    expect(e?.detail).toBe(raw);
  });
  it("leaves ordinary text alone", () => {
    expect(plainEventText("Level rose 20 cm").detail).toBeNull();
  });
});
