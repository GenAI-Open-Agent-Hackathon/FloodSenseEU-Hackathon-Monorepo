import type { DataOrigin } from "../types/views";

export function allSourcesAreSeed(rows: { source: string }[]): boolean {
  return rows.length > 0 && rows.every((row) => row.source.startsWith("seed:"));
}

export function originPill(
  origins: DataOrigin[],
  discharge?: { origin: DataOrigin; rows: { source: string }[] },
): { tone: "fixture" | "live" | "mixed"; label: string } {
  const live = origins.filter((origin) => origin === "live").length;
  if (live === 0) return { tone: "fixture", label: "Fixture · not live" };
  if (live === origins.length) {
    if (discharge?.origin === "live" && allSourcesAreSeed(discharge.rows)) {
      return { tone: "live", label: "API · seed rows" };
    }
    return { tone: "live", label: "Live view rows" };
  }
  return { tone: "mixed", label: "Mixed view rows" };
}
