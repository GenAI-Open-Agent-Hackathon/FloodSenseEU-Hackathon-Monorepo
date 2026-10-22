import { formatEur, formatInt } from "../../lib/format";
import type { PortfolioSite, TierExposure } from "../../types";

interface ExposureKpisProps {
  sites: readonly PortfolioSite[];
  tiers: readonly TierExposure[];
  pendingApprovals: number;
}

export function ExposureKpis({ sites, tiers, pendingApprovals }: ExposureKpisProps) {
  const totalValue = sites.reduce((sum, s) => sum + s.insuredValueEur, 0);
  const totalPolicies = sites.reduce((sum, s) => sum + s.policyCount, 0);
  const elevated = tiers.filter((t) => t.tier === "high" || t.tier === "severe");
  const elevatedValue = elevated.reduce((sum, t) => sum + t.insuredValueEur, 0);
  const elevatedPolicies = elevated.reduce((sum, t) => sum + t.policyCount, 0);

  return (
    <div className="kpis">
      <Kpi label="Insured value" value={formatEur(totalValue)} detail={`${sites.length} sites · ${formatInt(totalPolicies)} policies`} />
      <Kpi label="High + severe exposure" value={formatEur(elevatedValue)} detail={`${formatInt(elevatedPolicies)} policies`} tone="danger" />
      <Kpi label="Share at elevated risk" value={`${Math.round((elevatedValue / totalValue) * 100)}%`} detail="of insured value" tone="warn" />
      <Kpi label="Awaiting approval" value={String(pendingApprovals)} detail="outbound actions" tone="info" />
    </div>
  );
}

function Kpi({ label, value, detail, tone = "neutral" }: { label: string; value: string; detail: string; tone?: "neutral" | "danger" | "warn" | "info" }) {
  return (
    <div className={`kpi kpi--${tone}`}>
      <span className="kpi__label">{label}</span>
      <span className="kpi__value">{value}</span>
      <span className="kpi__detail">{detail}</span>
    </div>
  );
}
