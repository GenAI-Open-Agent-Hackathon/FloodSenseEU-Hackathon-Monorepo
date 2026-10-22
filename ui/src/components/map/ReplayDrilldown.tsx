import { gaugeStatus, gaugeStatusLabel } from "../../lib/gaugeStatus";
import type { LevelPoint, ReplayScenario, ReplayStation } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { ProvenanceBadge } from "../shared/ProvenanceBadge";
import { LevelChart } from "./LevelChart";
import { replayHourTime } from "./ReplayControls";

interface ReplayDrilldownProps {
  scenario: ReplayScenario;
  station: ReplayStation;
  hour: number;
  onClose: () => void;
}

/** Replay version of the gauge drill-down: levels up to the current replay hour. */
export function ReplayDrilldown({ scenario, station, hour, onClose }: ReplayDrilldownProps) {
  const points: LevelPoint[] = station.levelsCm.slice(0, hour + 1).map((cm, h) => ({ t: replayHourTime(scenario, h).toISOString(), cm }));
  const level = station.levelsCm[hour] ?? null;
  const status = gaugeStatus(level, station.thresholds);

  return (
    <aside className="drilldown" aria-label={`Replay gauge ${station.stationName}`}>
      <header className="drilldown__header">
        <div>
          <h3>
            {station.stationName} <span className="muted">· {station.river}</span>
          </h3>
          <p className="muted small">{scenario.title}</p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close gauge details">
          ×
        </button>
      </header>
      <div className={`drilldown__now gauge-status gauge-status--${status}`}>
        <span className="drilldown__level">{level ?? "–"}</span>
        <span className="muted"> cm</span>
        <span className="drilldown__status">{gaugeStatusLabel[status]}</span>
        <ProvenanceBadge provenance={scenario.provenance} />
      </div>
      <LevelChart
        observed={points}
        thresholds={station.thresholds}
        title={`Reconstructed water level at ${station.stationName} up to replay hour ${hour + 1}`}
        timeRange={{ start: scenario.startAt, end: replayHourTime(scenario, scenario.hours - 1).toISOString() }}
      />
      <p className="notice small">{scenario.disclaimer}</p>
      <CitedClaims variant="prose" claims={[{ id: "replay", text: "Replay curve is reconstructed for the demo.", citationIds: [scenario.citationId] }]} />
    </aside>
  );
}
