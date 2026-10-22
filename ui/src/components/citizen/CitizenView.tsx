import { useState, type ReactNode } from "react";
import { getDefaultRegionId, getGauges, getRiskAssessment, listLocations, listRegions } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { hideSplash } from "../../lib/splash";
import type { Location, Region } from "../../types";
import { GaugeMap } from "../map/GaugeMap";
import { AsyncBoundary } from "../shared/AsyncBoundary";
import { Card } from "../shared/Card";
import { MockBadge } from "../shared/MockBadge";
import { ProvenanceBadge } from "../shared/ProvenanceBadge";
import { AskPanel } from "./AskPanel";
import { GaugeList } from "./GaugeList";
import { LocationPicker } from "./LocationPicker";
import { RecommendedActions } from "./RecommendedActions";
import { RiskSummary } from "./RiskSummary";

/** Matches the default map region (Bavaria), so map and risk card agree on first load. */
const DEFAULT_LOCATION_ID = "passau";

interface CitizenData {
  locations: Location[];
  regions: Region[];
}

async function loadCitizenData(): Promise<CitizenData> {
  const [locations, regions] = await Promise.all([listLocations(), listRegions()]);
  return { locations, regions };
}

export function CitizenView() {
  const data = useAsync(loadCitizenData, []);
  return (
    <AsyncBoundary state={data} loadingText="Loading locations…">
      {({ locations, regions }) => <CitizenDashboard locations={locations} regions={regions} />}
    </AsyncBoundary>
  );
}

function CitizenDashboard({ locations, regions }: CitizenData) {
  const [locationId, setLocationId] = useState(DEFAULT_LOCATION_ID);
  const [regionId, setRegionId] = useState(getDefaultRegionId);
  const location = locations.find((l) => l.id === locationId) ?? locations[0];

  // Picking a location moves the map to its region; the region selector stays independent.
  const selectLocation = (id: string) => {
    setLocationId(id);
    const region = regions.find((r) => r.locationIds.includes(id));
    if (region) {
      setRegionId(region.id);
    }
  };

  if (!location) {
    return <p>No locations.</p>;
  }
  return (
    <LocationDashboard
      locations={locations}
      location={location}
      onSelect={selectLocation}
      map={<GaugeMap regions={regions} regionId={regionId} onRegionChange={setRegionId} onMapReady={hideSplash} />}
    />
  );
}

interface LocationDashboardProps {
  locations: readonly Location[];
  location: Location;
  onSelect: (id: string) => void;
  map: ReactNode;
}

function LocationDashboard({ locations, location, onSelect, map }: LocationDashboardProps) {
  const risk = useAsync(() => getRiskAssessment(location.id), [location.id]);
  const gauges = useAsync(() => getGauges(location.id), [location.id]);

  return (
    <div className="view">
      <div className="view__intro">
        <div>
          <h1>Is my area at risk, and why?</h1>
          <p className="muted">Plain-language flood risk with a source behind every sentence. Click a number to see the evidence.</p>
        </div>
        <MockBadge />
      </div>

      <LocationPicker locations={locations} selectedId={location.id} onSelect={onSelect} />

      <div className="grid grid--citizen">
        <Card title="Risk right now" className="span-2" ownerHint="Agents: Investigator + Skeptic + Judge">
          <AsyncBoundary state={risk} loadingText="Assessing risk…">
            {(assessment) => <RiskSummary assessment={assessment} placeName={location.name} />}
          </AsyncBoundary>
        </Card>

        <Card title="What should I do?" ownerHint="Agents + UI">
          <AsyncBoundary state={risk}>{(assessment) => <RecommendedActions actions={assessment.actions} />}</AsyncBoundary>
        </Card>

        <Card title="River gauges map" className="span-3" ownerHint="UI + Ingestion (PEGELONLINE)">
          {map}
        </Card>

        <Card title={`Gauges near ${location.name}`} ownerHint="Ingestion + Zetaris" aside={<ProvenanceBadge provenance="sample" />}>
          <AsyncBoundary state={gauges} loadingText="Reading gauges…">
            {(list) => <GaugeList gauges={list} />}
          </AsyncBoundary>
        </Card>

        <Card title="Ask a question" className="span-2" ownerHint="Agentic RAG + cache">
          <AskPanel locationId={location.id} placeName={location.name} />
        </Card>
      </div>
    </div>
  );
}
