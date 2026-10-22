import { formatTime } from "../../lib/format";
import type { GaugeReading, Trend } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { Sparkline } from "../shared/Sparkline";

const trendSymbol: Record<Trend, string> = { rising: "▲", steady: "▶", falling: "▼" };

export function GaugeList({ gauges }: { gauges: readonly GaugeReading[] }) {
  if (gauges.length === 0) {
    return <p className="muted">No gauges near this location.</p>;
  }
  return (
    <ul className="gauge-list">
      {gauges.map((gauge) => {
        const ratio = gauge.levelCm / gauge.warningLevelCm;
        const status = ratio >= 1 ? "over" : ratio >= 0.8 ? "near" : "ok";
        return (
          <li key={gauge.id} className={`gauge gauge--${status}`}>
            <div className="gauge__head">
              <div>
                <strong>{gauge.stationName}</strong>
                <span className="muted small">
                  {gauge.river} · {gauge.operator}
                </span>
              </div>
              <span className={`trend trend--${gauge.trend}`}>
                {trendSymbol[gauge.trend]} {gauge.trend}
              </span>
            </div>
            <div className="gauge__body">
              <div className="gauge__value">
                {gauge.levelCm}
                <small> cm</small>
              </div>
              <Sparkline values={gauge.history24h} threshold={gauge.warningLevelCm} label={`${gauge.stationName} last 24 hours`} />
            </div>
            <div className="gauge__bar" aria-label={`${Math.round(ratio * 100)}% of warning level`}>
              <span style={{ width: `${Math.min(100, ratio * 100)}%` }} />
            </div>
            <div className="gauge__foot muted small">
              <span>
                Warning level {gauge.warningLevelCm} cm · measured {formatTime(gauge.measuredAt)}
              </span>
              <CitedClaims claims={[{ id: gauge.id, text: "Source", citationIds: [gauge.citationId] }]} variant="prose" showSources={false} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
