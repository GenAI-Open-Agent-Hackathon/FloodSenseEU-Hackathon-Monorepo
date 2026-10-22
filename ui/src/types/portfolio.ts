import type { RiskLevel } from "./risk";

export interface PortfolioSite {
  id: string;
  name: string;
  city: string;
  region: string;
  country: string;
  lat: number;
  lon: number;
  policyCount: number;
  insuredValueEur: number;
  tier: RiskLevel;
  nearestGaugeId?: string;
}

/** Aggregated exposure for one risk tier. */
export interface TierExposure {
  tier: RiskLevel;
  siteCount: number;
  policyCount: number;
  insuredValueEur: number;
}

export interface Alert {
  id: string;
  severity: RiskLevel;
  title: string;
  region: string;
  /** ISO 8601 timestamp. */
  issuedAt: string;
  affectedSiteIds: string[];
  citationId: string;
}
