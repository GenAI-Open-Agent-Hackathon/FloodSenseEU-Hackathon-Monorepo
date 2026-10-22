import { riskLabel } from "../../lib/format";
import type { RiskLevel } from "../../types";

export function RiskBadge({ level, size = "md" }: { level: RiskLevel; size?: "sm" | "md" | "lg" }) {
  return <span className={`risk-badge risk-badge--${level} risk-badge--${size}`}>{riskLabel[level]}</span>;
}
