export type RouteId = "citizen" | "insurer";

export type EvidenceTopic = "discharge" | "rain";

export type NoticeTone = "info" | "sim";

export interface Notice {
  id: string;
  title: string;
  body: string;
  tone: NoticeTone;
  read: boolean;
}

export type DischargeBand = "low" | "typical" | "elevated" | "peak";

/** Demo threshold for the alert simulation. Not a warning level from the hazard view. */
export const SIMULATED_ALERT_M3S = 80;
