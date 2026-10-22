import type { RiskAssessment } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { CacheLabel } from "../shared/CacheLabel";
import { JudgeScoreBadge } from "../shared/JudgeScoreBadge";
import { RiskBadge } from "../shared/RiskBadge";

export function RiskSummary({ assessment, placeName }: { assessment: RiskAssessment; placeName: string }) {
  return (
    <div className={`risk-summary risk-summary--${assessment.level}`}>
      <div className="risk-summary__top">
        <div>
          <p className="eyebrow">Flood risk · next {assessment.horizonHours} h · {placeName}</p>
          <div className="risk-summary__level">
            <RiskBadge level={assessment.level} size="lg" />
            <span className="risk-summary__score" title="Composite risk score 0-100">
              {assessment.score}
              <small>/100</small>
            </span>
          </div>
        </div>
        <div className="risk-summary__meta">
          <CacheLabel cache={assessment.cache} />
          <JudgeScoreBadge score={assessment.judge} />
        </div>
      </div>
      <p className="risk-summary__headline">{assessment.headline}</p>
      <h3 className="section-title">Why?</h3>
      <CitedClaims claims={assessment.claims} />
    </div>
  );
}
