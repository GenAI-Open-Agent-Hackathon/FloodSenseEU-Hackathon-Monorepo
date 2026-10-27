import { useConsole } from "../context/ConsoleContext";
import { modeStripText } from "../lib/mode";
import { DemoChip } from "./ModeSwitch";

/**
 * Context strip under the header, on every page: the global mode in one sentence, "Live data · checked HH:MM" or
 * "Past flood: Ahr 2021 (replay)", the DEMO DATA chip when demo data is on, and Stop while a simulation plays.
 * A cached answer is labelled on the answer itself, never in this strip.
 */
export function ReplayBar() {
  const { modeState, liveCheckedAt, liveHealth, deskRoute, playing, stopSimulation } = useConsole();
  return (
    <div className="replay-bar" data-kind={modeState.mode === "past" ? "replay" : "live"} role="status" aria-live="polite">
      <span className="context-text">{modeStripText(modeState, liveCheckedAt, liveHealth, deskRoute.page)}</span>
      <DemoChip />
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
