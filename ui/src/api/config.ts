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
  /**
   * "Report a map issue" link. Set for OpenStreetMap, whose tile policy asks
   * for one. Omitted for any other provider.
   */
  reportIssueUrl?: string;
}

/**
 * Base map tiles. Defaults to the public OpenStreetMap tile server, which is
 * fine for a low-traffic demo under the OSM tile usage policy
 * (https://operations.osmfoundation.org/policies/tiles/). For production, set
 * VITE_MAP_TILE_URL and VITE_MAP_ATTRIBUTION to a hosted or commercial
 * provider together; the attribution must match the provider.
 */
const OSM_REPORT_ISSUE_URL = "https://www.openstreetmap.org/fixthemap";

const osmTiles: MapTileConfig = {
  url: OSM_TILE_URL,
  attributionHtml: OSM_ATTRIBUTION,
  maxZoom: 19,
  reportIssueUrl: OSM_REPORT_ISSUE_URL,
};

function readMapTiles(): MapTileConfig {
  const url = (env.VITE_MAP_TILE_URL ?? "").trim();
  const attribution = (env.VITE_MAP_ATTRIBUTION ?? "").trim();
  // Blank means the public OSM tiles. Their credit is fixed: a custom
  // attribution string must not replace it while those tiles are in use.
  if (!url || url === OSM_TILE_URL) {
    if (attribution && attribution !== OSM_ATTRIBUTION) {
      console.warn("OpenStreetMap tiles keep their own attribution. Set an HTTPS VITE_MAP_TILE_URL to use VITE_MAP_ATTRIBUTION.");
    }
    return osmTiles;
  }
  // A custom provider must be HTTPS and must bring its own attribution.
  // Otherwise stay on OSM rather than ship an uncredited or non-HTTPS URL.
  if (!url.startsWith("https://") || !attribution) {
    console.warn("Ignoring VITE_MAP_TILE_URL. A custom tile URL must be HTTPS and VITE_MAP_ATTRIBUTION must be set. Using OpenStreetMap.");
    return osmTiles;
  }
  return { url, attributionHtml: attribution, maxZoom: 19 };
}

export const mapTiles: MapTileConfig = readMapTiles();

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
