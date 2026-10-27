/**
 * Plain-language wording for citizen body text. Answer claims sometimes name database tables and columns;
 * the original sentence stays available under "Technical detail". Numbers and meaning are not changed.
 */
const TERMS: [RegExp, string][] = [
  [/\bfloodsense_seed\.discharge_daily\b/g, "the daily river-flow record"],
  [/\bfloodsense_seed\.hazard_timeline\b/g, "the hourly rain record"],
  [/\bfloodsense_seed\.exposure_join\b/g, "the insured-sites record"],
  [/\bfloodsense_seed\.provenance\b/g, "the source list"],
  [/\bfloodsense_seed\.\w+/g, "the stored record"],
  [/\bdischarge_daily\b/g, "the daily river-flow record"],
  [/\bhazard_timeline\b/g, "the hourly rain record"],
  [/\bwarning_level is null\b/g, "no official warning level is attached"],
  [/\bwarning_level\b/g, "warning level"],
  [/\bdischarge_m3s\b/g, "river flow"],
  [/\brain_mm\b/g, "rain"],
  [/ ?The source column is [^.]*\.\s?/g, " "],
  [/\bseed:open-meteo-flood-glofas\b/g, "Open-Meteo GloFAS model data"],
];

export function plainLanguage(text: string): string {
  let out = text;
  for (const [pattern, replacement] of TERMS) out = out.replace(pattern, replacement);
  return out.replace(/\s{2,}/g, " ").trim();
}
