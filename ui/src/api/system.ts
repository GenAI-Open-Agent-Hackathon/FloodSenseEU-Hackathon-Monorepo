import { apiBaseUrl, apiTimeoutMs } from "./config";

/** GET result: the JSON body, "missing" for a 404 (endpoint not deployed yet), or "down" when unreachable. */
export type Probe = { kind: "ok"; body: unknown } | { kind: "missing" } | { kind: "down" };

async function probe(path: string, signal?: AbortSignal, base = apiBaseUrl()): Promise<Probe> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), apiTimeoutMs());
  const onAbort = () => ctrl.abort();
  signal?.addEventListener("abort", onAbort);
  try {
    const r = await fetch(`${base}${path}`, { signal: ctrl.signal, credentials: "omit" });
    if (r.status === 404) return { kind: "missing" };
    if (!r.ok) return { kind: "down" };
    return { kind: "ok", body: await r.json() };
  } catch {
    return { kind: "down" };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

/** GET /config: agents flags and lanes. */
export const fetchConfig = (signal?: AbortSignal) => probe("/config", signal);
/** GET /system: component health. May 404 on builds without it; the caller treats that as unknown. */
export const fetchSystem = (signal?: AbortSignal) => probe("/system", signal);
