import { useNow } from "../../hooks/useNow";
import { minutesSince } from "../../lib/format";
import type { Alert } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { RiskBadge } from "../shared/RiskBadge";

export function AlertList({ alerts }: { alerts: readonly Alert[] }) {
  const now = useNow();
  return (
    <ul className="alert-list">
      {alerts.map((alert) => (
        <li key={alert.id} className={`alert alert--${alert.severity}`}>
          <RiskBadge level={alert.severity} size="sm" />
          <div className="alert__body">
            <CitedClaims claims={[{ id: alert.id, text: alert.title, citationIds: [alert.citationId] }]} variant="prose" showSources={false} />
            <span className="muted small">
              {alert.region} · {alert.affectedSiteIds.length} sites · {minutesSince(alert.issuedAt, now)} min ago
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
