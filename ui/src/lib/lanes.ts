/**
 * Display labels for judge model ids on the contract.
 *
 * Routing names and `deterministic` are shown as stored. A concrete
 * Nightshift id is "answered by" that model. Which model answers a routing
 * name today is the table at the top of docs/architecture/c4.md. Super VL
 * answers both lanes, so this label does not assign it to fast or deep.
 * Lightning is not shown as meterless/fast.
 */
const ANSWERED_BY: Record<string, string> = {
  "nvidia/nemotron-3.5-super-vl-120b-a12b": "answered by Nemotron 3.5 Super VL 120B A12B",
  "nvidia/nemotron-3.5-lightning-30b-a3b": "answered by Nemotron 3.5 Lightning 30B A3B",
};

export const NEBIUS_NAME = "Nebius Token Factory";
const PROVIDER_NAMES: Record<string, string> = { nightshift: "Nightshift", nebius: NEBIUS_NAME };

let llmBackend: string | null = null;
/** Set once from GET /platform/status (llm_backend). Until known, labels stay as the trace states them. */
export function setLlmBackend(b: string | null | undefined): void {
  llmBackend = b ? b.toLowerCase() : null;
}

/** providerOf, but a Nemotron id with no stated provider is named after the live backend (Nebius, else Nightshift). */
export function providerLabel(modelId: string, explicit?: string | null): string | null {
  const p = providerOf(modelId, explicit);
  return p === "Nightshift" && !(explicit ?? "").trim() && llmBackend === "nebius" ? NEBIUS_NAME : p;
}

/** Title of the language-model box: names the backend only when known. */
export function llmBoxTitle(backend: string | null | undefined): string {
  const b = (backend ?? "").toLowerCase();
  return b === "nebius" ? `${NEBIUS_NAME} · NVIDIA Nemotron` : b === "nightshift" ? "Nightshift · NVIDIA Nemotron" : "Language model · NVIDIA Nemotron";
}

/**
 * The one provider rule for model chips, pipeline badges and the live model line. The trace's explicit
 * provider wins when present; only without one does the id decide: an nvidia/...nemotron... id is
 * Nightshift, anything else is not guessed.
 */
export function providerOf(modelId: string, explicit?: string | null): string | null {
  const stated = (explicit ?? "").trim();
  if (stated) return PROVIDER_NAMES[stated.toLowerCase()] ?? stated;
  const id = modelId.toLowerCase();
  if (id.startsWith("nvidia/") && id.includes("nemotron")) return "Nightshift";
  return null;
}

export function laneLabel(modelId: string): string {
  return ANSWERED_BY[modelId] ?? modelId;
}
