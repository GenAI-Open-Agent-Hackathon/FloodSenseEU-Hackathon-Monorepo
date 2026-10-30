import type { ExposureJoinRow } from "../types/views";
import type { WatchSource } from "./euWatch";
import { headlineCounts } from "./places";
import { exposureStats } from "./series";

export interface Chip {
  label: string;
  /** null renders as "no data yet": never a made-up number. */
  value: string | null;
}

export const GOALS = {
  citizen: "Is my street at risk, and what do I do?",
  insurer: "Which insured sites are exposed, and what do we tell the customer?",
  operator: "Which rivers and places need attention first, and what do hotline staff tell callers?",
} as const;

/** Cited facts from docs/DECK-FACTS.md; none of these is on its "sources disagree" list. */
export const FACTS = {
  citizen: {
    text: "Turís, Spain, recorded 184.6 mm of rain in one hour on 29 Oct 2024, a new Spanish record.",
    source: "2024 Spanish floods, Wikipedia rev. 1379732613 (docs/DECK-FACTS.md, section 4 paragraph 3)",
  },
  insurer: {
    text: "Valencia 2024: Munich Re estimates 4.1 billion euros of 10.7 billion euros total damage were insured.",
    source: "2024 Spanish floods, Wikipedia rev. 1379732613 (docs/DECK-FACTS.md, section 5 paragraph 4)",
  },
  operator: {
    text: "Valencia alone accounted for 70% of flood-related deaths in Europe in 2024.",
    source: "2024 Spanish floods, Wikipedia rev. 1379732613 (docs/DECK-FACTS.md, section 5 paragraph 5)",
  },
} as const;

const n = (v: number) => v.toLocaleString("en-GB");

export function citizenChips(sources: readonly WatchSource[]): Chip[] {
  if (sources.length === 0) return [{ label: "Places watched", value: null }, { label: "At Watch or Elevated", value: null }];
  const c = headlineCounts(sources);
  return [
    { label: "Places watched", value: n(c.total) },
    { label: "At Watch or Elevated", value: n(c.gaugesAbove + c.gaugesNear + c.modelElevated + c.modelWatch) },
  ];
}

export function insurerChips(rows: readonly ExposureJoinRow[], watched: number): Chip[] {
  const s = rows.length > 0 ? exposureStats([...rows]) : null;
  return [
    { label: "Policies exposed (synthetic book)", value: s ? `${n(s.inFootprint)} of ${n(s.policies)}` : null },
    { label: "Sum insured exposed (synthetic)", value: s ? `EUR ${n(Math.round(s.sumInsured))}` : null },
    { label: "Live sources watched", value: watched > 0 ? n(watched) : null },
  ];
}

export function operatorChips(sources: readonly WatchSource[], scripts: number, pending: number | null): Chip[] {
  const attention = sources.length === 0 ? null : sources.filter((s) => s.status === "over" || s.status === "near").length;
  return [
    { label: "Places needing attention", value: attention === null ? null : n(attention) },
    { label: "Call scripts available", value: scripts > 0 ? n(scripts) : null },
    { label: "Approvals pending", value: pending === null ? null : n(pending) },
  ];
}
