import { getGaugeForecast, getGaugeObservations } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { gaugeStatusLabel } from "../../lib/gaugeStatus";
import type { Claim, GaugeStation } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { AsyncBoundary } from "../shared/AsyncBoundary";
import { ProvenanceBadge } from "../shared/ProvenanceBadge";
import { LevelChart } from "./LevelChart";

interface GaugeDrilldownProps {
  station: GaugeStation;
  onClose: () => void;
}

function formatTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "no current value";
}

/** 48-hour history, thresholds and a sample forecast band for one gauge. */
export function GaugeDrilldown({ station, onClose }: GaugeDrilldownProps) {
  const observations = useAsync(() => getGaugeObservations(station.id), [station.id]);
  const forecast = useAsync(() => getGaugeForecast(station.id), [station.id]);

  return (
    <aside className="drilldown" aria-label={`Gauge ${station.stationName}`}>
      <header className="drilldown__header">
        <div>
          <h3>
            {station.stationName} <span className="muted">· {station.river}</span>
          </h3>
          <p className="muted small">
            {station.operator} · {formatTime(station.measuredAt)}
          </p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close gauge details">
          ×
        </button>
      </header>

      <div className={`drilldown__now gauge-status gauge-status--${station.status}`}>
        <span className="drilldown__level">{station.levelCm ?? "–"}</span>
        <span className="muted"> cm</span>
        <span className="drilldown__status">{gaugeStatusLabel[station.status]}</span>
        <ProvenanceBadge provenance={station.provenance} />
      </div>

      <AsyncBoundary state={observations} loadingText="Loading the last 48 hours…">
        {(obs) => (
          <>
            <LevelChart
              observed={obs.points}
              forecast={forecast.status === "success" ? forecast.data.points : []}
              thresholds={station.thresholds}
              title={`Water level at ${station.stationName}, last 48 hours${forecast.status === "success" ? " and a 24-hour sample forecast band" : ""}`}
            />
            <div className="drilldown__provenance">
              <span>
                Last 48 h: <ProvenanceBadge provenance={obs.provenance} />
              </span>
              {forecast.status === "success" && (
                <span>
                  Forecast band: <ProvenanceBadge provenance={forecast.data.provenance} detail="not a real forecast" />
                </span>
              )}
            </div>
            {obs.fallbackReason && <p className="notice small">{obs.fallbackReason}</p>}
            <CitedClaims variant="prose" claims={drilldownClaims(station, obs.citationId, forecast.status === "success" ? forecast.data.citationId : null)} />
          </>
        )}
      </AsyncBoundary>

      {station.thresholds && <p className="muted small">Threshold: {station.thresholds.label}.</p>}
    </aside>
  );
}

function drilldownClaims(station: GaugeStation, observationsCitationId: string, forecastCitationId: string | null): Claim[] {
  const claims: Claim[] = [
    {
      id: "now",
      text: `Latest level at ${station.stationName}: ${station.levelCm ?? "n/a"} cm.`,
      citationIds: [station.citationId],
    },
  ];
  if (observationsCitationId !== station.citationId) {
    claims.push({ id: "history", text: "48-hour history.", citationIds: [observationsCitationId] });
  }
  if (forecastCitationId) {
    claims.push({ id: "forecast", text: "Forecast band is a sample model output.", citationIds: [forecastCitationId] });
  }
  return claims;
}
