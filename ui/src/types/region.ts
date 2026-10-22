/** WGS84 rectangle the map fits. Not a political outline. */
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
  gaugeFeed: GaugeFeed;
  /** Location ids (risk assessments) that belong to this region. */
  locationIds: string[];
  /**
   * Footer text when this region's gauges are sample data: there is no live
   * feed, the feed is disabled, or the request failed.
   */
  sampleAttribution: string;
}
