/**
 * Where a displayed value came from. The UI must label anything that is not
 * "live" so sample or reconstructed data is never mistaken for a measurement.
 */
export type DataProvenance = "live" | "sample" | "reconstructed";
