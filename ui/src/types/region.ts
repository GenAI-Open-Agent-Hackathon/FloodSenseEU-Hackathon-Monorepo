/** South-west and north-east corners as [lat, lon] pairs (WGS84). */
export interface BoundingBox {
  south: number;
  west: number;
  north: number;
  east: number;
}

/** Which backend serves the gauges for a region. */
export type GaugeFeed = "pegelonline" | "mock";

/** A map region the user can switch to. */
export interface Region {
  id: string;
  name: string;
  country: string;
  bounds: BoundingBox;
  /** Initial zoom level for the map. */
  zoom: number;
  gaugeFeed: GaugeFeed;
  /** Location ids (risk assessments) that belong to this region. */
  locationIds: string[];
}
