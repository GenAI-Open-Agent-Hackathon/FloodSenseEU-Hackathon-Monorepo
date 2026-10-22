/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** Leaflet tile URL template, e.g. https://tile.openstreetmap.org/{z}/{x}/{y}.png */
  readonly VITE_MAP_TILE_URL?: string;
  /** HTML attribution for the tile provider in VITE_MAP_TILE_URL. */
  readonly VITE_MAP_ATTRIBUTION?: string;
  /** "live" (default) or "mock". */
  readonly VITE_GAUGE_FEED?: "live" | "mock";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
