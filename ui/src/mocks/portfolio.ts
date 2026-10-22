import type { Alert, PortfolioSite } from "../types";
import { minutesAgo } from "./time";

/** Fictional insurer portfolio. MOCK DATA. */
export const portfolioSites: PortfolioSite[] = [
  { id: "s-01", name: "Ahrtor retail terrace", city: "Bad Neuenahr-Ahrweiler", region: "Rhineland-Palatinate", country: "DE", lat: 50.543, lon: 7.118, policyCount: 46, insuredValueEur: 18_400_000, tier: "high", nearestGaugeId: "g-bad-bodendorf" },
  { id: "s-02", name: "Kurpark residential block", city: "Bad Neuenahr-Ahrweiler", region: "Rhineland-Palatinate", country: "DE", lat: 50.547, lon: 7.125, policyCount: 112, insuredValueEur: 31_200_000, tier: "high", nearestGaugeId: "g-bad-bodendorf" },
  { id: "s-03", name: "Altenahr guesthouses", city: "Altenahr", region: "Rhineland-Palatinate", country: "DE", lat: 50.517, lon: 6.99, policyCount: 18, insuredValueEur: 6_900_000, tier: "high", nearestGaugeId: "g-altenahr" },
  { id: "s-04", name: "Deutz logistics hall", city: "Cologne", region: "North Rhine-Westphalia", country: "DE", lat: 50.94, lon: 6.98, policyCount: 4, insuredValueEur: 22_000_000, tier: "low", nearestGaugeId: "g-koeln" },
  { id: "s-05", name: "Rheinauhafen offices", city: "Cologne", region: "North Rhine-Westphalia", country: "DE", lat: 50.927, lon: 6.965, policyCount: 27, insuredValueEur: 54_500_000, tier: "moderate", nearestGaugeId: "g-koeln" },
  { id: "s-06", name: "Bonn Beuel housing", city: "Bonn", region: "North Rhine-Westphalia", country: "DE", lat: 50.737, lon: 7.12, policyCount: 88, insuredValueEur: 24_300_000, tier: "low", nearestGaugeId: "g-bonn" },
  { id: "s-07", name: "Altstadt shops", city: "Passau", region: "Bavaria", country: "DE", lat: 48.574, lon: 13.466, policyCount: 39, insuredValueEur: 12_700_000, tier: "moderate", nearestGaugeId: "g-passau-donau" },
  { id: "s-08", name: "Innstadt apartments", city: "Passau", region: "Bavaria", country: "DE", lat: 48.568, lon: 13.462, policyCount: 64, insuredValueEur: 19_800_000, tier: "moderate", nearestGaugeId: "g-passau-ingling" },
  { id: "s-09", name: "Paiporta warehouses", city: "Paiporta", region: "Valencian Community", country: "ES", lat: 39.428, lon: -0.418, policyCount: 12, insuredValueEur: 15_600_000, tier: "severe", nearestGaugeId: "g-poyo" },
  { id: "s-10", name: "Catarroja homes", city: "Catarroja", region: "Valencian Community", country: "ES", lat: 39.403, lon: -0.404, policyCount: 140, insuredValueEur: 28_900_000, tier: "severe", nearestGaugeId: "g-poyo" },
  { id: "s-11", name: "Manises industrial park", city: "Manises", region: "Valencian Community", country: "ES", lat: 39.49, lon: -0.46, policyCount: 9, insuredValueEur: 33_100_000, tier: "high", nearestGaugeId: "g-turia" },
  { id: "s-12", name: "Ciutat Vella flats", city: "Valencia", region: "Valencian Community", country: "ES", lat: 39.475, lon: -0.376, policyCount: 75, insuredValueEur: 21_400_000, tier: "moderate", nearestGaugeId: "g-turia" },
];

export const alerts: Alert[] = [
  { id: "al-1", severity: "severe", title: "Rambla del Poyo flow rising sharply", region: "Valencian Community", issuedAt: minutesAgo(12), affectedSiteIds: ["s-09", "s-10"], citationId: "cit-saih-poyo" },
  { id: "al-2", severity: "high", title: "Ahr above first warning threshold at Altenahr", region: "Rhineland-Palatinate", issuedAt: minutesAgo(38), affectedSiteIds: ["s-01", "s-02", "s-03"], citationId: "cit-rlp-altenahr" },
  { id: "al-3", severity: "moderate", title: "Danube approaching reporting level 1 at Passau", region: "Bavaria", issuedAt: minutesAgo(95), affectedSiteIds: ["s-07", "s-08"], citationId: "cit-hnd-passau" },
  { id: "al-4", severity: "low", title: "Rhine at Cologne slightly elevated", region: "North Rhine-Westphalia", issuedAt: minutesAgo(180), affectedSiteIds: ["s-04", "s-05"], citationId: "cit-pegel-koeln" },
];
