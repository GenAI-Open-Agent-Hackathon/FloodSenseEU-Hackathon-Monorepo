import { parseSystem, type SystemStatus } from "../lib/system";
import { apiBaseUrl, apiTimeoutMs } from "./config";

export type SystemFetch = { status: SystemStatus | null; error: string | null };

/** GET /system once. A failure is an error string, never a throw. */
export async function fetchSystem(base = apiBaseUrl()): Promise<SystemFetch> {
  try {
    const response = await fetch(`${base}/system`, {
      credentials: "omit",
      cache: "no-store",
      signal: AbortSignal.timeout(apiTimeoutMs()),
    });
    if (!response.ok) return { status: null, error: `GET /system returned ${response.status}` };
    const status = parseSystem(await response.json());
    return status ? { status, error: null } : { status: null, error: "GET /system did not return an object" };
  } catch {
    return { status: null, error: `API not reached at ${base}/system` };
  }
}
