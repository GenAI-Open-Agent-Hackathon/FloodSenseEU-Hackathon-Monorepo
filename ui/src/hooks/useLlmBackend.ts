import { useEffect, useSyncExternalStore } from "react";
import { fetchPlatformStatus } from "../api/platform";
import { getLlmBackend, setLlmBackend, subscribeLlmBackend } from "../lib/lanes";

/** The live LLM backend ("nebius", "nightshift", ...) or null while unknown. Re-renders when it arrives. */
export const useLlmBackend = (): string | null => useSyncExternalStore(subscribeLlmBackend, getLlmBackend);

/** The one GET /platform/status for the shell. A failure leaves the backend unknown (neutral wording). */
export function useLoadLlmBackend(): void {
  useEffect(() => {
    let live = true;
    void fetchPlatformStatus().then((r) => live && setLlmBackend(r.status?.llmBackend));
    return () => {
      live = false;
    };
  }, []);
}
