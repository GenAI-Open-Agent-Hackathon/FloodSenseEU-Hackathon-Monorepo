/**
 * PEGELONLINE REST API v2 adapter (German federal waterway gauges, WSV).
 * Docs: https://www.pegelonline.wsv.de/webservice/dokuRestapi
 * Licence: DL-DE->Zero-2.0. Values are unchecked raw data without warranty.
 *
 * This file only knows the wire format. Caching and fallback live in gauges.ts.
 */
import type { BoundingBox, GaugeThresholds, LevelPoint } from "../types";
import { pegelonline } from "./config";

// --- Wire types (only the fields we use) ------------------------------------

interface PoCharacteristicValue {
  shortname: string;
  value: number;
  timespanStart?: string;
  timespanEnd?: string;
}

interface PoCurrentMeasurement {
  timestamp: string;
  value: number;
  stateMnwMhw?: "low" | "normal" | "high" | "unknown" | "commented" | "out-dated";
}

interface PoTimeseries {
  shortname: string;
  unit: string;
  currentMeasurement?: PoCurrentMeasurement;
  characteristicValues?: PoCharacteristicValue[];
}

export interface PoStation {
  uuid: string;
  number: string;
  shortname: string;
  longname: string;
  agency: string;
  latitude?: number;
  longitude?: number;
  water: { shortname: string; longname: string };
  timeseries?: PoTimeseries[];
}

interface PoMeasurement {
  timestamp: string;
  value: number;
}

// --- Requests ----------------------------------------------------------------

async function getJson<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), pegelonline.timeoutMs);
  try {
    // Default browser caching and Referer behaviour; no extra headers.
    const response = await fetch(`${pegelonline.baseUrl}${path}`, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`PEGELONLINE responded ${response.status}`);
    }
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timer);
  }
}

const EARTH_RADIUS_KM = 6371;

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(a));
}

function contains(bounds: BoundingBox, lat: number, lon: number): boolean {
  return lat >= bounds.south && lat <= bounds.north && lon >= bounds.west && lon <= bounds.east;
}

/**
 * Stations with a water-level ("W") timeseries inside a bounding box.
 * The API has no bbox filter, so we query the circle around the box and
 * filter client-side: one request per region.
 */
export async function fetchStationsInBounds(bounds: BoundingBox): Promise<PoStation[]> {
  const lat = (bounds.south + bounds.north) / 2;
  const lon = (bounds.west + bounds.east) / 2;
  const radiusKm = Math.ceil(haversineKm(lat, lon, bounds.north, bounds.east));
  const query = new URLSearchParams({
    timeseries: "W",
    includeTimeseries: "true",
    includeCurrentMeasurement: "true",
    includeCharacteristicValues: "true",
    latitude: lat.toFixed(4),
    longitude: lon.toFixed(4),
    radius: String(radiusKm),
  });
  const stations = await getJson<PoStation[]>(`/stations.json?${query.toString()}`);
  return stations.filter((s) => s.latitude !== undefined && s.longitude !== undefined && contains(bounds, s.latitude, s.longitude));
}

/** Water-level measurements for the last `hours`, downsampled to one point per hour. */
export async function fetchHourlyLevels(stationUuid: string, hours: number): Promise<LevelPoint[]> {
  const raw = await getJson<PoMeasurement[]>(`/stations/${encodeURIComponent(stationUuid)}/W/measurements.json?start=PT${hours}H`);
  const byHour = new Map<string, LevelPoint>();
  for (const m of raw) {
    const hour = new Date(m.timestamp);
    hour.setMinutes(0, 0, 0);
    // Keep the last measurement within each hour.
    byHour.set(hour.toISOString(), { t: m.timestamp, cm: m.value });
  }
  return [...byHour.values()];
}

// --- Mapping helpers -------------------------------------------------------

export function waterLevelSeries(station: PoStation): PoTimeseries | undefined {
  return station.timeseries?.find((t) => t.shortname === "W");
}

function characteristic(series: PoTimeseries, shortname: string): number | undefined {
  return series.characteristicValues?.find((c) => c.shortname === shortname)?.value;
}

/** Share of the MW→MHW range at which a gauge turns amber. */
const NEAR_FRACTION = 0.75;

/**
 * PEGELONLINE publishes no official warning levels. As a proxy we use the
 * mean high water (MHW): red at or above MHW, amber from 75% of the way from
 * mean water (MW) to MHW. Returns null when the station has no MHW.
 */
export function proxyThresholds(series: PoTimeseries): GaugeThresholds | null {
  const mhw = characteristic(series, "MHW");
  if (mhw === undefined) {
    return null;
  }
  const mw = characteristic(series, "MW") ?? mhw * 0.6;
  return {
    warningCm: Math.round(mhw),
    nearCm: Math.round(mw + NEAR_FRACTION * (mhw - mw)),
    label: "MHW (mean high water), proxy, not an official warning level",
  };
}

/** Public station page, used as the citation URL. */
export function stationPageUrl(station: PoStation): string {
  return `https://pegelonline.wsv.de/gast/stammdaten?pegelnr=${encodeURIComponent(station.number)}`;
}

/** Title-cases the upper-case names PEGELONLINE uses ("PASSAU DONAU" → "Passau Donau"). */
export function titleCase(name: string): string {
  return name.toLowerCase().replace(/(^|[\s\-/(])(\p{L})/gu, (_, sep: string, letter: string) => sep + letter.toUpperCase());
}
