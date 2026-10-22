/**
 * Runtime configuration. Everything that differs between environments lives
 * here, read from VITE_* variables with safe public defaults.
 */
const env = import.meta.env;

/** FastAPI backend. Not called by the mock yet. */
export const apiBaseUrl: string = env.VITE_API_URL ?? "http://localhost:18000";

const OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION =
  '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>';

export interface MapTileConfig {
  /** Leaflet URL template. Must be HTTPS. */
  url: string;
  /** HTML attribution shown on the map. Required by the tile provider; never hide it. */
  attributionHtml: string;
  maxZoom: number;
  /** "Report a map issue" link recommended by the OSM tile usage policy. */
  reportIssueUrl: string;
}

/**
 * Base map tiles. Defaults to the public OpenStreetMap tile server, which is
 * fine for a low-traffic demo under the OSM tile usage policy
 * (https://operations.osmfoundation.org/policies/tiles/). For production, set
 * VITE_MAP_TILE_URL and VITE_MAP_ATTRIBUTION to a hosted or commercial
 * provider together; the attribution must match the provider.
 */
export const mapTiles: MapTileConfig = {
  url: env.VITE_MAP_TILE_URL ?? OSM_TILE_URL,
  attributionHtml: env.VITE_MAP_ATTRIBUTION ?? OSM_ATTRIBUTION,
  maxZoom: 19,
  reportIssueUrl: "https://www.openstreetmap.org/fixthemap",
};

export interface PegelonlineConfig {
  baseUrl: string;
  /** Set VITE_GAUGE_FEED=mock to never call PEGELONLINE (offline demos). */
  enabled: boolean;
  /** Client-side cache lifetime; PEGELONLINE updates most gauges every 15 minutes. */
  cacheTtlMs: number;
  timeoutMs: number;
  /** Recommended source note (DL-DE->Zero-2.0 does not require attribution). */
  attribution: string;
  licenceName: string;
  licenceUrl: string;
}

export const pegelonline: PegelonlineConfig = {
  baseUrl: "https://www.pegelonline.wsv.de/webservices/rest-api/v2",
  enabled: env.VITE_GAUGE_FEED !== "mock",
  cacheTtlMs: 5 * 60_000,
  timeoutMs: 10_000,
  attribution: "© www.pegelonline.wsv.de",
  licenceName: "DL-DE->Zero-2.0",
  licenceUrl: "https://www.govdata.de/dl-de/zero-2-0",
};
