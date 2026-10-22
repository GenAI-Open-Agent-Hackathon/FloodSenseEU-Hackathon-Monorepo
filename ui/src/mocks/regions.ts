import type { Region } from "../types";

/**
 * Map regions. Bounding boxes are rectangles around each area, so they also
 * include some gauges just across the border. Bavaria is the start view.
 */
export const regions: Region[] = [
  {
    id: "bavaria",
    name: "Bavaria",
    country: "DE",
    bounds: { south: 47.27, west: 8.97, north: 50.56, east: 13.84 },
    gaugeFeed: "pegelonline",
    locationIds: ["passau"],
    sampleAttribution: "Sample values for this region, not PEGELONLINE measurements.",
  },
  {
    id: "nrw",
    name: "North Rhine-Westphalia",
    country: "DE",
    bounds: { south: 50.32, west: 5.87, north: 52.53, east: 9.46 },
    gaugeFeed: "pegelonline",
    locationIds: ["cologne"],
    sampleAttribution: "Sample values for this region, not PEGELONLINE measurements.",
  },
  {
    id: "rlp",
    name: "Rhineland-Palatinate",
    country: "DE",
    bounds: { south: 48.97, west: 6.11, north: 50.94, east: 8.51 },
    gaugeFeed: "pegelonline",
    locationIds: ["bad-neuenahr-ahrweiler"],
    sampleAttribution: "Sample values for this region, not PEGELONLINE measurements.",
  },
  {
    id: "valencia",
    name: "Valencia",
    country: "ES",
    bounds: { south: 39.12, west: -0.85, north: 39.62, east: -0.2 },
    // PEGELONLINE covers German federal waterways only; SAIH Júcar is mocked.
    gaugeFeed: "mock",
    locationIds: ["valencia"],
    sampleAttribution: "SAIH Júcar (CHJ): sample values, not measurements.",
  },
];

export const DEFAULT_REGION_ID = "bavaria";
