import { useEffect, useState } from "react";
import { fetchGaugeLevels, type GaugeLoad } from "../api/gauges";

export type GaugeState = GaugeLoad | { state: "loading"; rows: []; detail: string };

let shared: Promise<GaugeLoad> | null = null;

/** One request per page load, shared by every widget that shows gauges. */
export function useGaugeLevels(): GaugeState {
  const [load, setLoad] = useState<GaugeState>({ state: "loading", rows: [], detail: "" });
  useEffect(() => {
    let alive = true;
    shared ??= fetchGaugeLevels();
    void shared.then((result) => {
      if (alive) setLoad(result);
    });
    return () => {
      alive = false;
    };
  }, []);
  return load;
}
