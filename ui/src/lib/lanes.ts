/**
 * Display labels for judge model ids already on the contract.
 * The contract ModelId union is Ayush's to change. This map does not.
 */
const LANE_LABELS: Record<string, string> = {
  "nvidia/nemotron-3-super-120b-a12b": "meterless/deep",
  "nvidia/nemotron-3.5-lightning-30b-a3b": "meterless/fast",
};

export function laneLabel(modelId: string): string {
  return LANE_LABELS[modelId] ?? modelId;
}
