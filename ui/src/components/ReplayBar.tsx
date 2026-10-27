import { useConsole } from "../context/ConsoleContext";
import { replayBarView } from "../lib/events";

/**
 * Context strip under the header. "Live data" on Now, a plain "Viewing: ... (replay of a past event)"
 * on pages that show a replayed event, nothing elsewhere. While the simulation plays, Stop stays
 * reachable on every page. A cached answer is labelled on the answer itself, never in this strip.
 */
export function ReplayBar() {
  const { date, playing, stopSimulation, deskRoute, eventId, ahrDate, sitesView } = useConsole();
  const liveSites = deskRoute.role === "insurer" && deskRoute.page === "sites" && sitesView === "live";
  const view = liveSites ? ({ kind: "none", text: "" } as const) : replayBarView(deskRoute, eventId, { date }, { date: ahrDate });
  if (view.kind === "none" && !playing) return null;

  return (
    <div className="replay-bar" data-kind={view.kind}>
      {view.kind !== "none" && <span className="context-text">{view.text}</span>}
      {playing && (
        <>
          <span className="replay-state" data-playing="true">
            Simulation playing
          </span>
          <button type="button" className="button replay-stop" onClick={stopSimulation}>
            Stop
          </button>
        </>
      )}
    </div>
  );
}
