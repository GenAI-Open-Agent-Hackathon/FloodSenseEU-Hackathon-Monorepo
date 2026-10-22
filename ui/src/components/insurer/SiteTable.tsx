import { formatEur, riskLevels } from "../../lib/format";
import type { PortfolioSite } from "../../types";
import { RiskBadge } from "../shared/RiskBadge";

/** Sites sorted by tier (most severe first), then by insured value. */
export function SiteTable({ sites }: { sites: readonly PortfolioSite[] }) {
  const sorted = [...sites].sort(
    (a, b) => riskLevels.indexOf(b.tier) - riskLevels.indexOf(a.tier) || b.insuredValueEur - a.insuredValueEur,
  );
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Site</th>
            <th scope="col">City</th>
            <th scope="col">Tier</th>
            <th scope="col" className="num">Policies</th>
            <th scope="col" className="num">Insured</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((site) => (
            <tr key={site.id}>
              <td>{site.name}</td>
              <td className="muted">{site.city}</td>
              <td>
                <RiskBadge level={site.tier} size="sm" />
              </td>
              <td className="num">{site.policyCount}</td>
              <td className="num">{formatEur(site.insuredValueEur)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
