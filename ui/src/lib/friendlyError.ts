/** Friendly, role-aware error text for the Ask chat. Raw detail goes behind "Technical detail", with hosts and URLs removed. */

export type ErrorKind = "unavailable" | "timeout" | "unreadable" | "not_found" | "failed" | "other";

export interface FriendlyError {
  kind: ErrorKind;
  text: string;
  retry: boolean;
  /** Offer the latest recorded answer, labelled not live. */
  offerRecorded: boolean;
  /** Raw detail with URLs and internal hosts stripped. Empty when there is nothing left. */
  technical: string;
}

/** Remove URLs and host:port pairs (http://agents:8100, agents:8100, 10.0.0.5:8000, localhost:18000). */
export function stripInternal(text: string): string {
  return text
    .replace(/\b[a-z][a-z0-9+.-]*:\/\/[^\s"'<>),;]+/gi, "[internal address]")
    .replace(/\b(?:[a-z0-9-]+(?:\.[a-z0-9-]+)*|\d{1,3}(?:\.\d{1,3}){3}):\d{2,5}\b/gi, "[internal address]")
    .replace(/(?:\s*\bat\s+\[internal address\])+/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/** Pure: classify from an HTTP status (if any) and the raw message. */
export function classifyError(status: number | null, raw: string): ErrorKind {
  const m = raw.toLowerCase();
  if (status === 422) return "unreadable";
  if (status === 404 || /not found/.test(m)) return "not_found";
  if (status === 504 || status === 408 || /timed? ?out|timeout|taking longer|lost contact/.test(m)) return "timeout";
  if (status === 502 || status === 503 || (status === null && /unreachable|could not reach|network|failed to fetch|remoteprotocolerror|connect/.test(m)) || /unreachable|remoteprotocolerror|connecterror/.test(m))
    return "unavailable";
  if (/failed/.test(m) || (status !== null && status >= 500)) return "failed";
  return "other";
}

export function friendlyError(status: number | null, raw: string, role: "citizen" | "insurer" | string = "insurer"): FriendlyError {
  const kind = classifyError(status, raw);
  const citizen = role === "citizen";
  const technical = stripInternal(raw);
  switch (kind) {
    case "unavailable":
      return {
        kind,
        text: citizen
          ? "Our agents are restarting or busy right now. Here is the latest recorded answer while you wait. For official warnings, follow your local authorities."
          : "Our agents are restarting or busy right now. Here is the latest recorded answer while you wait.",
        retry: true,
        offerRecorded: true,
        technical,
      };
    case "timeout":
      return { kind, text: "This is taking longer than usual… The agents may still finish; you can retry in a moment.", retry: true, offerRecorded: true, technical };
    case "unreadable":
      return { kind, text: "I couldn't read that question — try rephrasing.", retry: false, offerRecorded: false, technical };
    case "not_found":
      return { kind, text: "That run stopped before it could start properly. Please try again.", retry: true, offerRecorded: false, technical };
    case "failed":
      return {
        kind,
        text: citizen ? "Something went wrong while preparing your answer. Please try again." : "The run did not finish. Nothing was sent. Please try again.",
        retry: true,
        offerRecorded: true,
        technical,
      };
    default:
      return { kind, text: "Something went wrong. Please try again.", retry: true, offerRecorded: false, technical };
  }
}

/** Pure: an HTTP status from a message like "The service failed (503): …", else null. */
export function statusFromMessage(raw: string): number | null {
  const m = /\((\d{3})\)/.exec(raw);
  return m ? Number(m[1]) : null;
}
