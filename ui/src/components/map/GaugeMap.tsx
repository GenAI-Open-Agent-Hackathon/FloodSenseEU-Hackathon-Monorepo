import { useMemo, useState } from "react";
import { getRegionGauges, getReplayScenario, listReplayScenarios, pegelonlineConfig } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { useReplayPlayer } from "../../hooks/useReplayPlayer";
import { gaugeStatus } from "../../lib/gaugeStatus";
import type { GaugeStation, Region, RegionGauges, ReplayScenario } from "../../types";
import { AsyncBoundary } from "../shared/AsyncBoundary";
import { ProvenanceBadge } from "../shared/ProvenanceBadge";
import { GaugeDrilldown } from "./GaugeDrilldown";
import { LeafletMap, type MapMarker } from "./LeafletMap";
import { MapLegend } from "./MapLegend";
import { RegionSelector } from "./RegionSelector";
import { ReplayControls } from "./ReplayControls";
import { ReplayDrilldown } from "./ReplayDrilldown";

type MapMode = "now" | "replay";

interface GaugeMapProps {
  regions: readonly Region[];
  regionId: string;
  onRegionChange: (id: string) => void;
  onMapReady?: () => void;
}

/** Region map with current gauges, a drill-down panel and the historic replay. */
export function GaugeMap({ regions, regionId, onRegionChange, onMapReady }: GaugeMapProps) {
  const [mode, setMode] = useState<MapMode>("now");
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const scenarios = useAsync(listReplayScenarios, []);
  const region = regions.find((r) => r.id === regionId) ?? regions[0];

  const changeRegion = (id: string) => {
    setSelectedId(null);
    onRegionChange(id);
  };

  const startReplay = (id: string) => {
    const summary = scenarios.status === "success" ? scenarios.data.find((s) => s.id === id) : undefined;
    setMode("replay");
    setScenarioId(id);
    setSelectedId(null);
    if (summary) {
      onRegionChange(summary.regionId);
    }
  };

  const showNow = () => {
    setMode("now");
    setSelectedId(null);
  };

  if (!region) {
    return <p className="muted">No map regions configured.</p>;
  }

  return (
    <div className="gauge-map">
      <div className="gauge-map__toolbar">
        <RegionSelector regions={regions} selectedId={region.id} onSelect={changeRegion} disabled={mode === "replay"} />
        <div className="segmented" role="radiogroup" aria-label="Map mode">
          <button type="button" role="radio" aria-checked={mode === "now"} className={`segmented__option ${mode === "now" ? "is-active" : ""}`} onClick={showNow}>
            Now
          </button>
          {scenarios.status === "success" &&
            scenarios.data.map((s) => (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={mode === "replay" && scenarioId === s.id}
                className={`segmented__option ${mode === "replay" && scenarioId === s.id ? "is-active" : ""}`}
                onClick={() => startReplay(s.id)}
              >
                Replay: {s.title}
              </button>
            ))}
        </div>
      </div>

      {mode === "replay" && scenarioId ? (
        <ReplayPanel scenarioId={scenarioId} region={region} selectedId={selectedId} onSelect={setSelectedId} onMapReady={onMapReady} />
      ) : (
        <NowPanel region={region} selectedId={selectedId} onSelect={setSelectedId} onMapReady={onMapReady} />
      )}
    </div>
  );
}

interface LayerProps {
  region: Region;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onMapReady?: () => void;
}

function stationLabel(station: { stationName: string; river: string }, levelCm: number | null): string {
  return `${station.stationName} (${station.river}): ${levelCm === null ? "no value" : `${levelCm} cm`}`;
}

function NowPanel({ region, selectedId, onSelect, onMapReady }: LayerProps) {
  const gauges = useAsync(() => getRegionGauges(region.id), [region.id]);
  const data = gauges.status === "success" ? gauges.data : null;
  const markers = useMemo<MapMarker[]>(
    () =>
      (data?.stations ?? []).map((s) => ({
        id: s.id,
        lat: s.lat,
        lon: s.lon,
        status: s.status,
        label: stationLabel(s, s.levelCm),
        isSample: s.provenance !== "live",
      })),
    [data],
  );
  const selected = data?.stations.find((s) => s.id === selectedId) ?? null;

  return (
    <>
      <div className="gauge-map__body">
        <LeafletMap bounds={region.bounds} markers={markers} selectedId={selectedId} onSelect={onSelect} onReady={onMapReady} ariaLabel={`Map of ${region.name} with river gauges`} />
        <div className="gauge-map__side">
          {selected ? <GaugeDrilldown key={selected.id} station={selected} onClose={() => onSelect(null)} /> : <AsyncBoundary state={gauges} loadingText="Loading gauges…">{(g) => <RegionSummary gauges={g} onSelect={onSelect} />}</AsyncBoundary>}
        </div>
      </div>
      <MapLegend />
      {data && <FeedFooter gauges={data} />}
    </>
  );
}

function RegionSummary({ gauges, onSelect }: { gauges: RegionGauges; onSelect: (id: string) => void }) {
  const counts = { over: 0, near: 0, ok: 0, unknown: 0 };
  for (const s of gauges.stations) {
    counts[s.status] += 1;
  }
  const highest = [...gauges.stations]
    .filter((s) => s.status === "over" || s.status === "near")
    .sort((a, b) => (a.status === b.status ? 0 : a.status === "over" ? -1 : 1))
    .slice(0, 4);

  return (
    <div className="region-summary">
      <p>
        <strong>{gauges.stations.length} gauges</strong> in view: <span className="status-count status-count--over">{counts.over} above</span>, <span className="status-count status-count--near">{counts.near} near</span>, <span className="status-count status-count--ok">{counts.ok} below</span>
        {counts.unknown > 0 && <>, {counts.unknown} without threshold</>}.
      </p>
      {highest.length > 0 && (
        <ul className="region-summary__list">
          {highest.map((s: GaugeStation) => (
            <li key={s.id}>
              <button type="button" className="link-button" onClick={() => onSelect(s.id)}>
                {s.stationName} ({s.river})
              </button>{" "}
              <span className="muted small">{s.levelCm} cm</span>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">Click a marker to see its last 48 hours.</p>
    </div>
  );
}

function FeedFooter({ gauges }: { gauges: RegionGauges }) {
  const fetched = new Date(gauges.fetchedAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const live = gauges.stations.filter((s) => s.provenance === "live").length;
  return (
    <div className="feed-footer small">
      <ProvenanceBadge provenance={gauges.provenance} detail={gauges.provenance === "live" ? `${live} federal gauges, fetched ${fetched}${gauges.fromCache ? " (cached)" : ""}` : undefined} />
      {gauges.stations.length > live && <ProvenanceBadge provenance="sample" detail="state-portal gauges (dashed)" />}
      {gauges.fallbackReason && <span className="notice">{gauges.fallbackReason}</span>}
      <span className="muted">
        Federal gauges: {pegelonlineConfig.attribution}, licence{" "}
        <a href={pegelonlineConfig.licenceUrl} target="_blank" rel="noopener noreferrer">
          {pegelonlineConfig.licenceName}
        </a>
        . Raw data, unchecked; colours use a proxy threshold, not official warnings.
      </span>
    </div>
  );
}

function ReplayPanel({ scenarioId, region, selectedId, onSelect, onMapReady }: LayerProps & { scenarioId: string }) {
  const scenario = useAsync(() => getReplayScenario(scenarioId), [scenarioId]);
  return (
    <AsyncBoundary state={scenario} loadingText="Loading replay…">
      {(s) => <ReplayMap scenario={s} region={region} selectedId={selectedId} onSelect={onSelect} onMapReady={onMapReady} />}
    </AsyncBoundary>
  );
}

function ReplayMap({ scenario, region, selectedId, onSelect, onMapReady }: LayerProps & { scenario: ReplayScenario }) {
  const player = useReplayPlayer(scenario.hours, scenario.id);
  const markers = useMemo<MapMarker[]>(
    () =>
      scenario.stations.map((s) => {
        const level = s.levelsCm[player.hour] ?? null;
        return { id: s.id, lat: s.lat, lon: s.lon, status: gaugeStatus(level, s.thresholds), label: stationLabel(s, level), isSample: true };
      }),
    [scenario, player.hour],
  );
  const selected = scenario.stations.find((s) => s.id === selectedId) ?? null;

  return (
    <>
      <p className="replay-banner" role="note">
        <strong>{scenario.disclaimer}</strong> Hour-by-hour replay of {scenario.title}; levels are synthetic curves shaped like the event.
      </p>
      <div className="gauge-map__body">
        <LeafletMap bounds={region.bounds} markers={markers} selectedId={selectedId} onSelect={onSelect} onReady={onMapReady} ariaLabel={`Replay map: ${scenario.title}`} />
        <div className="gauge-map__side">
          {selected ? (
            <ReplayDrilldown scenario={scenario} station={selected} hour={player.hour} onClose={() => onSelect(null)} />
          ) : (
            <p className="muted small">Press play, or click a marker to follow one gauge through the event.</p>
          )}
        </div>
      </div>
      <ReplayControls scenario={scenario} player={player} />
      <MapLegend />
    </>
  );
}
