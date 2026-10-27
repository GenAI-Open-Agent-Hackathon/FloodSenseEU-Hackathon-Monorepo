/**
 * General safety guidance a citizen sees before any reviewed, tailored step.
 * Not written for the UI: CITIZEN_ADVICE is verbatim the advice the agents already append to every
 * citizen answer (agents/floodsense_agents/live.py, CITIZEN_ADVICE). safety.test.ts fails if the two drift.
 * WARNING_LINKS is the only place official warning-service URLs live (allowlist in safety.test.ts).
 */
export type WarningCountry = "de" | "es";

export interface WarningLink {
  label: string;
  url: string;
}

export const WARNING_LINKS: Record<WarningCountry, { title: string; links: readonly WarningLink[] }> = {
  de: {
    title: "Germany",
    links: [
      { label: "NINA warning app (BBK)", url: "https://www.bbk.bund.de/DE/Warnung-Vorsorge/Warn-App-NINA/warn-app-nina_node.html" },
      { label: "Current warnings (warnung.bund.de)", url: "https://warnung.bund.de" },
      { label: "DWD weather warnings", url: "https://www.dwd.de/DE/wetter/warnungen_gemeinden/warnWetter_node.html" },
      { label: "Länder flood centres", url: "https://www.hochwasserzentralen.de" },
    ],
  },
  es: {
    title: "Spain · Valencia",
    links: [
      { label: "Protección Civil", url: "https://www.proteccioncivil.es" },
      { label: "AEMET warnings", url: "https://www.aemet.es/es/eltiempo/prediccion/avisos" },
      { label: "112 Comunitat Valenciana", url: "https://www.112cv.gva.es" },
    ],
  },
};

export const EMERGENCY_LINE = "In an emergency call 112.";

// JS \b is ASCII-only, so accented names match by their ASCII stem.
const GERMAN =
  /\b(?:AHR\d{2}|ahr|altenahr|ahrweiler|schuld|dernau|rhine|rhein|koeln|cologne|bonn|koblenz|mosel|germany|deutschland)\b|k(?:ö|oe)ln/i;
const SPANISH = /\b(?:VAL\d{2}|valencia|paiporta|catarroja|alfafar|chiva|utiel|spain)\b|\b(?:sedav|benet|algemes|espa[nñ]a)/i;

/** Pure: which countries' warning services fit the shown place. Unclear (or both) gives both, Spain first only when Spanish. */
export function warningCountriesFor(...shown: (string | null | undefined)[]): WarningCountry[] {
  const text = shown.filter(Boolean).join(" ");
  const de = GERMAN.test(text);
  const es = SPANISH.test(text);
  if (de && !es) return ["de"];
  if (es && !de) return ["es"];
  return ["de", "es"];
}
export const SAFETY_HEADLINE = "Follow your official warning service";

export const CITIZEN_ADVICE =
  "What to do: follow the official warnings (Germany: Hochwassermeldedienst of your Land, " +
  "DWD, NINA app; Spain: AEMET, ES-Alert, Protección Civil); keep away from riverbanks, " +
  "underpasses and cellars; call 112 in an emergency.";

export const CITIZEN_ADVICE_SOURCE = "Same advice the FloodSense agents give with every citizen answer";

export const GATE_LINE = "A tailored step from our agents appears here after a person checks it.";
