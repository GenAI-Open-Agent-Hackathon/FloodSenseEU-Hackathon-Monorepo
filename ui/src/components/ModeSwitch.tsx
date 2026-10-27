import { useState, type ReactNode } from "react";
import { useConsole } from "../context/ConsoleContext";
import { demoSnapshotText, DEMO_CHIP_TEXT } from "../lib/demo";
import { EVENT_META, type EventId } from "../lib/events";
import { PAST_EVENTS } from "../lib/mode";
import "../styles/mode.css";

/** The "DEMO DATA" chip. Shown wherever demo data is on, so demo rows are never mistaken for live ones. */
export function DemoChip({ className = "" }: { className?: string }) {
  const { demo } = useConsole();
  if (!demo) return null;
  return (
    <span className={`demo-chip ${className}`.trim()} title={`Bundled snapshot of ${demoSnapshotText()}. Not live.`}>
      {DEMO_CHIP_TEXT}
    </span>
  );
}

/** The global mode switch in the header: Live | Past flood (with the event), and the Demo data toggle. */
export function ModeSwitch() {
  const { mode, setMode, eventId, setEventId, demo, setDemo } = useConsole();
  return (
    <div className="mode-row" role="group" aria-label="Data mode">
      <div className="mode-seg" role="group" aria-label="Mode">
        <button type="button" aria-pressed={mode === "live"} onClick={() => setMode("live")}>
          Live
        </button>
        <button type="button" aria-pressed={mode === "past"} onClick={() => setMode("past")}>
          Past flood
        </button>
      </div>
      {mode === "past" && (
        <label className="mode-event">
          <span className="sr-only">Past flood</span>
          <select value={eventId} aria-label="Past flood event" onChange={(event) => setEventId(event.target.value as EventId)}>
            {PAST_EVENTS.map((id) => (
              <option key={id} value={id}>
                {EVENT_META[id].short}
              </option>
            ))}
          </select>
        </label>
      )}
      <button
        type="button"
        role="switch"
        aria-checked={demo}
        className="mode-switch"
        title="Swap the live readings for a bundled snapshot. Chat is not affected."
        onClick={() => setDemo(!demo)}
      >
        <span className="mode-switch__track" aria-hidden="true">
          <span className="mode-switch__thumb" />
        </span>
        <span>Demo data</span>
      </button>
      <DemoChip />
    </div>
  );
}

/** "Live data unavailable — show demo data?" Offered when the API or every live view fails; never switches on its own. */
export function DemoOffer() {
  const { demo, setDemo, healthChecked, healthOk, liveFailed, mode } = useConsole();
  const [dismissed, setDismissed] = useState(false);
  if (demo || dismissed || mode === "past") return null;
  if (!(healthChecked && !healthOk) && !liveFailed) return null;
  return (
    <div className="demo-offer" role="status">
      <span>Live data unavailable — show demo data?</span>
      <button type="button" className="button primary" onClick={() => setDemo(true)}>
        Show demo data
      </button>
      <button type="button" className="button ghost" onClick={() => setDismissed(true)}>
        Not now
      </button>
    </div>
  );
}

/** Past mode on a page that only has a live form: say so, and offer the one click back. */
export function SwitchToLive({ title, children }: { title: string; children?: ReactNode }) {
  const { setMode, modeState } = useConsole();
  return (
    <section className="card mode-gate" aria-label={title}>
      <p className="section-label">Past flood: {EVENT_META[modeState.eventId].short} (replay)</p>
      <h2>{title}</h2>
      <p>{children}</p>
      <div className="button-row">
        <button type="button" className="button primary" onClick={() => setMode("live")}>
          Switch to Live to see this
        </button>
      </div>
    </section>
  );
}

/** Live mode on a page that only shows a past flood: pick one (this switches the whole console to Past flood). */
export function ChoosePast({ title, children }: { title: string; children?: ReactNode }) {
  const { setEventId } = useConsole();
  return (
    <section className="card mode-gate" aria-label={title}>
      <p className="section-label">Live data</p>
      <h2>{title}</h2>
      <p>{children}</p>
      <div className="button-row">
        {PAST_EVENTS.map((id) => (
          <button key={id} type="button" className="button primary" onClick={() => setEventId(id)}>
            Show {EVENT_META[id].short}
          </button>
        ))}
      </div>
    </section>
  );
}
