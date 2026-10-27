import type { Probe } from "../api/system";

/** Status dot on a How it works box. */
export type DotState = "ok" | "off" | "down" | "unknown";

export const DOT_TEXT: Record<DotState, string> = {
  ok: "running",
  off: "switched off",
  down: "not reachable",
  unknown: "status unknown",
};

export type BoxId =
  | "router"
  | "agents"
  | "zetaris"
  | "feeds"
  | "nightshift"
  | "memory"
  | "rag"
  | "redis"
  | "human";

const rec = (v: unknown): Record<string, unknown> | null =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;

/** The body itself, or its `data` envelope. */
function unwrap(p: Probe): Record<string, unknown> | null {
  if (p.kind !== "ok") return null;
  const body = rec(p.body);
  return rec(body?.data) ?? body;
}

function flag(config: Record<string, unknown> | null, name: string): DotState {
  const v = rec(config?.flags)?.[name];
  if (v === true) return "ok";
  if (v === false) return "off";
  return config ? "ok" : "unknown";
}

function healthWord(v: unknown): DotState | null {
  if (v === true) return "ok";
  if (v === false) return "down";
  if (typeof v === "string") {
    const s = v.toLowerCase();
    if (/^(ok|up|healthy|ready|live|running|green)$/.test(s)) return "ok";
    if (/^(off|disabled)$/.test(s)) return "off";
    if (/^(down|error|failed|unhealthy|red|unreachable)$/.test(s)) return "down";
  }
  const r = rec(v);
  if (r) return healthWord(r.status ?? r.ok ?? r.state ?? r.healthy);
  return null;
}

/** Look up a component in a /system body, whatever its exact shape (flat, `components`, `services`, `checks`). */
export function systemStatus(system: Probe, names: string[]): DotState | null {
  const body = unwrap(system);
  if (!body) return null;
  const pools = [body, rec(body.components), rec(body.services), rec(body.checks)].filter(
    (p): p is Record<string, unknown> => p !== null,
  );
  for (const pool of pools) {
    for (const [key, value] of Object.entries(pool)) {
      if (names.some((n) => key.toLowerCase().includes(n))) {
        const s = healthWord(value);
        if (s) return s;
      }
    }
  }
  return null;
}

/** Pure: every box's dot from GET /config and GET /system. A missing /system (404) leaves its boxes unknown, never red. */
export function boxStatuses(config: Probe, system: Probe): Record<BoxId, DotState> {
  const cfg = unwrap(config);
  const agentsUp: DotState = config.kind === "ok" ? "ok" : config.kind === "down" ? "down" : "unknown";
  const sys = (names: string[], fallback: DotState): DotState => systemStatus(system, names) ?? fallback;
  const lanes = rec(cfg?.lanes);
  return {
    router: sys(["router", "front_door", "front-door"], agentsUp),
    agents: sys(["agents"], agentsUp),
    zetaris: sys(["zetaris"], "unknown"),
    feeds: sys(["feeds", "open_meteo", "open-meteo", "pegel"], cfg ? (rec(cfg.flags)?.FF_LIVE_DATA === true ? "ok" : "off") : "unknown"),
    nightshift: sys(["nightshift", "llm", "nemotron"], lanes && (lanes.fast || lanes.deep) ? "ok" : agentsUp === "ok" ? "unknown" : agentsUp),
    memory: sys(["hmem", "h-mem", "meterless", "memory"], flag(cfg, "FF_HMEM")),
    rag: sys(["pgvector", "rag", "nim", "embed"], flag(cfg, "FF_RAG_DOCS")),
    redis: sys(["redis", "cache"], "unknown"),
    human: flag(cfg, "FF_HITL"),
  };
}

/** "live feeds" or "seed data" for the data box, from FF_LIVE_DATA. */
export function feedsMode(config: Probe): "live feeds" | "seed data" | null {
  const cfg = unwrap(config);
  if (!cfg) return null;
  return rec(cfg.flags)?.FF_LIVE_DATA === true ? "live feeds" : "seed data";
}
