import { ServingLine } from "./Banners";
import { useConsole } from "../context/ConsoleContext";
import { replayBarView } from "../lib/events";
import { formatDay } from "../lib/format";

/**
 * Shared date, point, and playback state. Simulate starts on Alerts; Stop is here on every page.
 * The date and point follow the event the page shows (`replayBarView`); Simulate steps the Valencia
 * date only, so on an Ahr page the strip names it as the Valencia simulation instead of Playing/Paused.
 * On Approvals and Review the answer serving line rides in the same strip, so there is one banner.
 */
export function ReplayBar() {
  const { date, pointId, playing, points, stopSimulation, route, page, deskRoute, eventId, ahrDate, ahrPointId } =
    useConsole();
  const showServing = route === "insurer" && (page === "approvals" || page === "review");
  const view = replayBarView(deskRoute, eventId, { date, pointId, points }, { date: ahrDate, pointId: ahrPointId }, playing);

  return (
    <div className="replay-bar">
      <span className="section-label">Replay</span>
      <strong>{formatDay(view.date)}</strong>
      <span>{view.place}</span>
      {view.playback === "valencia" && (
        <span className="replay-state" data-playing={playing ? "true" : "false"}>
          {playing ? "Playing" : "Paused"}
        </span>
      )}
      {view.playback === "valencia-elsewhere" && (
        <span className="replay-state" data-playing="true">
          Valencia simulation playing
        </span>
      )}
      {playing && (
        <button type="button" className="button replay-stop" onClick={stopSimulation}>
          Stop
        </button>
      )}
      {showServing && <ServingLine inline />}
    </div>
  );
}