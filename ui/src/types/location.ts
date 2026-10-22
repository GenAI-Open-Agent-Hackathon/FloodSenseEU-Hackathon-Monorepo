export interface Location {
  id: string;
  name: string;
  region: string;
  /** ISO 3166-1 alpha-2 country code. */
  country: string;
  lat: number;
  lon: number;
  /** Main river shown on the schematic map. */
  river: string;
}
