import { formatEur, riskLabel } from "../../lib/format";
import type { TierExposure } from "../../types";

/** Horizontal bar chart of insured value per risk tier. Plain SVG-free markup. */
export function TierExposureChart({ tiers }: { tiers: readonly TierExposure[] }) {
  const max = Math.max(...tiers.map((t) => t.insuredValueEur), 1);
  return (
    <div className="tier-chart" role="table" aria-label="Insured value by risk tier">
      {tiers.map((t) => (
        <div key={t.tier} className="tier-chart__row" role="row">
          <span className="tier-chart__label" role="rowheader">
            {riskLabel[t.tier]}
          </span>
          <span className="tier-chart__track" role="cell">
            <span className={`tier-chart__bar tier-chart__bar--${t.tier}`} style={{ width: `${(t.insuredValueEur / max) * 100}%` }} />
          </span>
          <span className="tier-chart__value" role="cell">
            {formatEur(t.insuredValueEur)}
            <small>
              {t.siteCount} sites · {t.policyCount} pol.
            </small>
          </span>
        </div>
      ))}
    </div>
  );
}
