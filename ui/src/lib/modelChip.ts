import { shortModel } from "./liveRun";

/** Display names for the Nemotron ids the agents run. */
const MODEL_NAMES: Record<string, string> = {
  "nvidia/nemotron-3.5-lightning-30b-a3b": "Nemotron 3.5 Lightning 30B",
  "nvidia/nemotron-3.5-super-vl-120b-a12b": "Nemotron 3.5 Super VL 120B",
};

export function modelName(modelId: string): string {
  return MODEL_NAMES[modelId] ?? shortModel(modelId);
}

function llmIds(modelId: string | null | undefined): string[] {
  return (modelId ?? "")
    .split(",")
    .map((m) => m.trim())
    .filter((m) => m && m !== "deterministic");
}

/**
 * The model chip for one agent step, from the trace `model_id` and `lane` (fast / deep / sql):
 * "Nemotron 3.5 Lightning 30B · Nightshift fast lane", "SQL · Zetaris", or "rules" for a deterministic step.
 */
export function modelChip(modelId: string | null | undefined, lane: string | null | undefined): string {
  const ids = llmIds(modelId);
  const l = (lane ?? "").toLowerCase();
  if (ids.length) {
    const id = ids[ids.length - 1];
    const name = modelName(id);
    const nemotron = id.toLowerCase().startsWith("nvidia/") && id.toLowerCase().includes("nemotron");
    if (!nemotron) return name;
    const laneWord = l === "deep" ? "deep lane" : l === "fast" ? "fast lane" : null;
    return laneWord ? `${name} · Nightshift ${laneWord}` : `${name} · Nightshift`;
  }
  if (l === "sql") return "SQL · Zetaris";
  return "rules";
}

/** The run-level model: "Nemotron 3.5 Lightning 30B via Nightshift", or the bare id for any other model. */
export function runModelLine(modelIds: readonly string[]): string | null {
  const ids = modelIds.flatMap((m) => llmIds(m));
  if (!ids.length) return null;
  const id = ids[ids.length - 1];
  const nemotron = id.toLowerCase().startsWith("nvidia/") && id.toLowerCase().includes("nemotron");
  return nemotron ? `${modelName(id)} via Nightshift` : modelName(id);
}
