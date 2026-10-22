import type { PortfolioSite, TierExposure } from "../types";
import { riskLevels } from "./format";

/** Aggregates sites into one row per risk tier, always in tier order. */
export function exposureByTier(sites: readonly PortfolioSite[]): TierExposure[] {
  return riskLevels.map((tier) => {
    const inTier = sites.filter((site) => site.tier === tier);
    return {
      tier,
      siteCount: inTier.length,
      policyCount: inTier.reduce((sum, site) => sum + site.policyCount, 0),
      insuredValueEur: inTier.reduce((sum, site) => sum + site.insuredValueEur, 0),
    };
  });
}
