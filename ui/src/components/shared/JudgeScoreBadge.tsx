import { formatPercent } from "../../lib/format";
import type { JudgeScore } from "../../types";

const verdictLabel: Record<JudgeScore["verdict"], string> = {
  pass: "Judge: pass",
  "needs-review": "Judge: needs review",
  fail: "Judge: fail",
};

/** Compact Judge score. Set `detailed` to show the sub-scores and rationale. */
export function JudgeScoreBadge({ score, detailed = false }: { score: JudgeScore; detailed?: boolean }) {
  return (
    <div className={`judge judge--${score.verdict}`}>
      <span className="judge__pill">
        {verdictLabel[score.verdict]} · {score.overall.toFixed(2)}
      </span>
      {detailed && (
        <>
          <dl className="judge__metrics">
            <Metric label="Groundedness" value={score.groundedness} />
            <Metric label="Citation coverage" value={score.citationCoverage} />
            <Metric label="Skeptic resolved" value={score.skepticResolution} />
          </dl>
          <p className="judge__rationale">{score.rationale}</p>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="judge__metric">
      <dt>{label}</dt>
      <dd>
        <span className="judge__bar" aria-hidden="true">
          <span style={{ width: formatPercent(value) }} />
        </span>
        {formatPercent(value)}
      </dd>
    </div>
  );
}
