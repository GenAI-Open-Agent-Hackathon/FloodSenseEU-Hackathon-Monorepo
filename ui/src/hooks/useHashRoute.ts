import { useCallback, useEffect, useState } from "react";

export type Route = "citizen" | "insurer";

function readRoute(): Route {
  return window.location.hash === "#/insurer" ? "insurer" : "citizen";
}

/** Minimal hash router: #/citizen and #/insurer. No dependency needed for two views. */
export function useHashRoute(): [Route, (route: Route) => void] {
  const [route, setRoute] = useState<Route>(readRoute);

  useEffect(() => {
    const onChange = () => setRoute(readRoute());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback((next: Route) => {
    window.location.hash = `#/${next}`;
  }, []);

  return [route, navigate];
}
