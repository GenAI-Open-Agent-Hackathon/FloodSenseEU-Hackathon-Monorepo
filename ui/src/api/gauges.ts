/**
 * Map data: regions, gauges per region, and the drill-down series.
 *
 * Federal waterway gauges come live from PEGELONLINE (with a 5-minute client
 * cache) and fall back to sample stations when the feed is unreachable.
 * State-portal gauges (HND Bayern, Hochwasserportal NRW, RLP, SAIH Júcar) are
 * always sample data until their licence terms are checked.
 */
import { buildForecastBand } from "../mocks/forecast";
import { buildSampleHistory } from "../mocks/history";
import { DEFAULT_REGION_ID, regions } from "../mocks/regions";
import { sampleFederalStations, sampleStateStations } from "../mocks/stations";
import { gaugeStatus } from "../lib/gaugeStatus";
import type { GaugeForecast, GaugeObservations, GaugeStation, GaugeStatus, Region, RegionGauges } from "../types";
import { contentHash, registerCitation } from "./citations";
import { pegelonline } from "./config";
import { notFound, respond } from "./mockTransport";
import {
  fetchHourlyLevels,
  fetchStationsInBounds,
  proxyThresholds,
  stationPageUrl,
  titleCase,
  waterLevelSeries,
  type PoStation,
} from "./pegelonline";
import { TtlCache } from "./ttlCache";

const LIVE_ID_PREFIX = "pegelonline:";
const HISTORY_HOURS = 48;

const regionCache = new TtlCache<GaugeStation[]>(pegelonline.cacheTtlMs);
const historyCache = new TtlCache<GaugeObservations>(pegelonline.cacheTtlMs);

/** Every station handed out so far, so drill-down calls can look them up by id. */
const knownStations = new Map<string, GaugeStation>();

function remember(stations: readonly GaugeStation[]): void {
  stations.forEach((s) => knownStations.set(s.id, s));
}

export function listRegions(): Promise<Region[]> {
  return respond(regions, 50);
}

export function getDefaultRegionId(): string {
  return DEFAULT_REGION_ID;
}

// --- Live mapping --------------------------------------------------------------

function liveStatus(station: PoStation, levelCm: number | null, thresholds: GaugeStation["thresholds"]): GaugeStatus {
  if (thresholds) {
    return gaugeStatus(levelCm, thresholds);
  }
  // No MHW published: use PEGELONLINE's own MNW/MHW state if available.
  const state = waterLevelSeries(station)?.currentMeasurement?.stateMnwMhw;
  if (state === "high") return "over";
  if (state === "low" || state === "normal") return "ok";
  return "unknown";
}

async function toLiveStation(station: PoStation, fetchedAt: string): Promise<GaugeStation | null> {
  const series = waterLevelSeries(station);
  if (!series || station.latitude === undefined || station.longitude === undefined) {
    return null;
  }
  const current = series.currentMeasurement;
  const levelCm = current ? current.value : null;
  const thresholds = proxyThresholds(series);
  const citationId = `cit-pegelonline-${station.uuid}`;
  const quote = current
    ? `Water level (W) at ${station.longname} (${station.water.longname}): ${current.value} ${series.unit} at ${current.timestamp}.`
    : `No current water-level measurement for ${station.longname}.`;

  registerCitation({
    id: citationId,
    url: stationPageUrl(station),
    title: `PEGELONLINE: gauge ${station.longname} (${station.water.longname}), water level`,
    publisher: "Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV)",
    accessedAt: fetchedAt,
    locator: { section: current ? `Current measurement, ${current.timestamp}` : "Station master data" },
    quote,
    quoteIsSample: false,
    contentHash: await contentHash(quote),
    license: `${pegelonline.licenceName}; source: ${pegelonline.attribution}; unchecked raw data`,
    storage: "full-text",
  });

  return {
    id: `${LIVE_ID_PREFIX}${station.uuid}`,
    stationName: titleCase(station.longname),
    river: titleCase(station.water.longname),
    operator: `WSV ${titleCase(station.agency)} (PEGELONLINE)`,
    lat: station.latitude,
    lon: station.longitude,
    levelCm,
    measuredAt: current?.timestamp ?? null,
    thresholds,
    status: liveStatus(station, levelCm, thresholds),
    citationId,
    provenance: "live",
  };
}

async function loadLiveStations(region: Region): Promise<GaugeStation[]> {
  const raw = await fetchStationsInBounds(region.bounds);
  const fetchedAt = new Date().toISOString();
  const mapped = await Promise.all(raw.map((s) => toLiveStation(s, fetchedAt)));
  return mapped.filter((s): s is GaugeStation => s !== null);
}

function describeError(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "request timed out";
  }
  return error instanceof Error ? error.message : String(error);
}

// --- Public functions -----------------------------------------------------

/**
 * All gauges to draw for a region: federal gauges (live or sample) plus
 * state-portal gauges (sample). Cached for 5 minutes per region.
 */
export async function getRegionGauges(regionId: string): Promise<RegionGauges> {
  const region = regions.find((r) => r.id === regionId);
  if (!region) {
    throw notFound("Region", regionId);
  }
  const stateStations = sampleStateStations[regionId] ?? [];

  if (region.gaugeFeed === "pegelonline" && pegelonline.enabled) {
    try {
      const { value, storedAt, fromCache } = await regionCache.getOrLoad(regionId, () => loadLiveStations(region));
      const stations = [...value, ...stateStations];
      remember(stations);
      return {
        regionId,
        stations,
        provenance: "live",
        fetchedAt: new Date(storedAt).toISOString(),
        fromCache,
        attribution: `Federal gauges: ${pegelonline.attribution} (${pegelonline.licenceName}, unchecked raw data)`,
      };
    } catch (error) {
      return sampleRegionGauges(regionId, `PEGELONLINE could not be reached (${describeError(error)}).`);
    }
  }
  const reason = region.gaugeFeed === "pegelonline" ? "Live feed disabled (VITE_GAUGE_FEED=mock)." : undefined;
  return sampleRegionGauges(regionId, reason);
}

function sampleRegionGauges(regionId: string, fallbackReason: string | undefined): Promise<RegionGauges> {
  const stations = [...(sampleFederalStations[regionId] ?? []), ...(sampleStateStations[regionId] ?? [])];
  remember(stations);
  return respond(
    {
      regionId,
      stations,
      provenance: "sample",
      fetchedAt: new Date().toISOString(),
      fromCache: false,
      fallbackReason,
      attribution: regionId === "valencia" ? "SAIH Júcar (CHJ): sample values" : "Sample values",
    },
    200,
  );
}

function sampleObservations(station: GaugeStation, fallbackReason?: string): GaugeObservations {
  const end = station.measuredAt ?? new Date().toISOString();
  return {
    stationId: station.id,
    points: station.levelCm === null ? [] : buildSampleHistory(station.id, station.levelCm, end, HISTORY_HOURS),
    provenance: "sample",
    citationId: station.citationId,
    fallbackReason,
  };
}

/** Hourly levels for the last 48 hours: live for PEGELONLINE gauges, else sample. */
export async function getGaugeObservations(stationId: string): Promise<GaugeObservations> {
  const station = knownStations.get(stationId);
  if (!station) {
    throw notFound("Gauge", stationId);
  }
  if (!stationId.startsWith(LIVE_ID_PREFIX)) {
    return respond(sampleObservations(station), 150);
  }
  const uuid = stationId.slice(LIVE_ID_PREFIX.length);
  try {
    const { value } = await historyCache.getOrLoad(stationId, async () => ({
      stationId,
      points: await fetchHourlyLevels(uuid, HISTORY_HOURS),
      provenance: "live",
      citationId: station.citationId,
    }));
    return value;
  } catch (error) {
    return sampleObservations(station, `PEGELONLINE measurements could not be loaded (${describeError(error)}).`);
  }
}

/** 24-hour forecast band. Always SAMPLE: no forecast model is connected yet. */
export function getGaugeForecast(stationId: string): Promise<GaugeForecast> {
  const station = knownStations.get(stationId);
  if (!station || station.levelCm === null) {
    return Promise.reject(notFound("Forecast for gauge", stationId));
  }
  const trend = station.status === "over" ? 4 : station.status === "near" ? 2.5 : 0.4;
  return respond(
    {
      stationId,
      points: buildForecastBand(station.levelCm, trend, station.measuredAt ?? new Date().toISOString()),
      provenance: "sample",
      citationId: "cit-forecast-band",
    },
    180,
  );
}
