import { useEffect, useMemo, useState } from "react";
import { useConsole } from "../context/ConsoleContext";
import { useLiveWatch } from "../hooks/useLiveWatch";
import { assessContext, assessQuestion, LEVEL_TEXT, monitorView, type AlertRow } from "../lib/alertMonitor";
import { onTrackedRuns, runForKey, startAssessment, trackedLine, trackedRuns, type AssessOutcome, type TrackedRun } from "../lib/assessRuns";
import { rehearsalAt, rehearsalQuestion } from "../lib/rehearsal";
import { REPLAY_EVENTS, buildFrames, dayStarts, crossingText, isDailyDischarge, type DisasterEvent } from "../lib/disasterReplay";
import { ahrFixture, loadAhrRows, type EventRows } from "../lib/replaySource";
import { EVENT_META } from "../lib/events";
import { routeHref } from "../lib/route";
import { RefMarks } from "./RefMarks";
import "../styles/insurer.css";

function useTracked(): TrackedRun[] {
  const [runs, setRuns] = useState<TrackedRun[]>(() => trackedRuns());
  useEffect(() => onTrackedRuns(setRuns), []);
  return runs;
}

/** "14:05 UTC, 27 Oct" for a reading time; the date alone for a model as-of day. */
function readingTime(iso: string | null): string {
  if (!iso) return "time not reported";
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return `model run of ${iso}`;
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return iso;
  const d = new Date(t);
  const hm = `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} UTC`;
  return `${hm}, ${d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })}`;
}

/**
 * One button that starts one real agent run. Never automatic: each run costs model calls. The run then follows
 * the normal path (stream, Judge, human review) and lands in Approvals.
 */
function AssessButton({
  runKey,
  label,
  build,
}: {
  runKey: string;
  label: string;
  build: () => Parameters<typeof startAssessment>[0];
}) {
  const runs = useTracked();
  const run = runForKey(runs, runKey);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<AssessOutcome | null>(null);
  const active = run?.status === "running";
  const press = async () => {
    setBusy(true);
    setOutcome(null);
    try {
      setOutcome(await startAssessment(build()));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="assess">
      <button type="button" className="button primary" disabled={busy || active} onClick={() => void press()}>
        {busy ? "Starting…" : active ? "Agents working…" : label}
      </button>
      <p className="assess__status small" role="status" aria-live="polite">
        {run ? (
          <>
            {trackedLine(run)}
            {(run.status === "running" || run.status === "awaiting_approval") && (
              <>
                {" "}
                · <a href={routeHref("insurer", "approvals")}>Open Approvals</a>
              </>
            )}
          </>
        ) : outcome && outcome.kind !== "started" ? (
          outcome.message
        ) : (
          "Starts one full agent run (several model calls). Nothing runs until you press it."
        )}
      </p>
    </div>
  );
}

function AlertItem({ row }: { row: AlertRow }) {
  const { llmProvider, llmProviders } = useConsole();
  const s = row.source;
  return (
    <li className={`alert-row alert-row--${row.level}`}>
      <div className="alert-row__main">
        <span className={`level-chip level-chip--${row.level}`}>
          {LEVEL_TEXT[row.level]}
          {s.kind === "model" ? " · model" : ""}
        </span>
        <div className="alert-row__text">
          <p className="alert-row__place">
            <strong>
              {s.river} · {s.name}
            </strong>{" "}
            <span className="muted small">{s.country}</span> <RefMarks nums={row.refs.map((r) => r.n)} refs={row.refs} />
          </p>
          <p className="muted small">
            {s.value} · {row.basis} · {readingTime(row.at)}
          </p>
        </div>
      </div>
      <AssessButton
        runKey={`alert:${row.id}`}
        label="Ask the agents to assess"
        build={() => ({
          key: `alert:${row.id}`,
          question: assessQuestion(row),
          context: assessContext(row),
          provider: llmProvider,
          allowedProviders: llmProviders,
        })}
      />
    </li>
  );
}

/** Every live watched source at Watch or Warning, from gauge_levels (official MHW band) and eu_watch (model band). */
function LiveAlertMonitor() {
  const watch = useLiveWatch();
  const view = monitorView({
    gauges: watch.gauges,
    points: watch.points,
    gaugeQueryId: watch.gaugeQueryId,
    modelQueryId: watch.modelQueryId,
    missing: watch.missing,
    state: watch.state,
    checkedAt: watch.checkedAt,
  });
  return (
    <section className="card monitor" aria-labelledby="monitor-title">
      <div className="card-head">
        <div>
          <p className="section-label">Live alert monitor</p>
          <h2 id="monitor-title">Watched sources at Watch or Warning</h2>
        </div>
        <span className={`chip ${view.kind === "alerts" ? "chip--stale" : view.kind === "calm" ? "chip--live" : ""}`}>
          {view.kind === "loading" ? "Checking" : view.kind === "unavailable" ? "No data" : "Live"}
        </span>
      </div>
      <p className={`monitor__headline monitor__headline--${view.kind}`} role="status">
        {view.text}
      </p>
      {view.kind === "alerts" && (
        <ul className="alert-rows">
          {view.rows.map((row) => (
            <AlertItem key={row.id} row={row} />
          ))}
        </ul>
      )}
      {(view.kind === "alerts" || view.kind === "calm") && view.notLive > 0 && (
        <p className="note">
          {view.notLive} elevated reading{view.notLive === 1 ? " is" : "s are"} stale or seed data and {view.notLive === 1 ? "is" : "are"} not raised as an alert.
        </p>
      )}
      <p className="note">
        Gauges: PEGELONLINE water level against the station's official MHW (mean high water), via Zetaris gauge_levels. Model points:
        GloFAS 7-day forecast against each point's own past 30 days, via Zetaris eu_watch, a model and not an official warning. Re-read
        every 5 minutes. Watch = near the line, Warning = above it.
      </p>
    </section>
  );
}

/** Step a past flood day by day; when a point crosses the line, offer a real agent run for that replay moment. */
function Rehearsal() {
  const desk = useConsole();
  const [eventId, setEventId] = useState<DisasterEvent["eventId"]>("EMSR517");
  const event = REPLAY_EVENTS.find((e) => e.eventId === eventId) ?? REPLAY_EVENTS[0];
  const [ahrRows, setAhrRows] = useState<EventRows>(() => ahrFixture());
  useEffect(() => {
    const controller = new AbortController();
    void loadAhrRows(REPLAY_EVENTS[0], controller.signal).then((rows) => {
      if (!controller.signal.aborted) setAhrRows(rows);
    });
    return () => controller.abort();
  }, []);
  const data = useMemo<EventRows>(
    () =>
      eventId === "EMSR517"
        ? ahrRows
        : {
            rows: desk.hazard.rows,
            points: desk.points.map((p) => ({ point_id: p.point_id, name: p.name })),
            source: `hazard_timeline (${desk.hazard.origin})`,
            badge: desk.hazard.origin === "fixture" ? "Bundled view extract, not from Zetaris" : `Zetaris · hazard_timeline (${desk.hazard.origin})`,
            fromZetaris: desk.hazard.origin !== "fixture",
          },
    [eventId, ahrRows, desk.hazard, desk.points],
  );
  const frames = useMemo(() => buildFrames(data.rows, event), [data.rows, event]);
  const days = useMemo(() => dayStarts(frames), [frames]);
  const daily = useMemo(() => isDailyDischarge(data.rows), [data.rows]);
  const [dayIndex, setDayIndex] = useState(0);
  useEffect(() => setDayIndex(0), [eventId]);
  const day = days[Math.min(dayIndex, Math.max(days.length - 1, 0))];
  const state = useMemo(() => (day ? rehearsalAt(data.rows, frames, event.thresholdM3s, day.index, data.points) : null), [data, frames, event, day]);
  const { llmProvider, llmProviders } = desk;

  return (
    <section className="card rehearsal" aria-labelledby="rehearsal-title">
      <div className="card-head">
        <div>
          <p className="section-label">Rehearse with a past flood</p>
          <h2 id="rehearsal-title">{event.name}</h2>
        </div>
        <span className="chip chip--sample">Replay · not live</span>
      </div>
      <div className="dr-events" role="group" aria-label="Past flood">
        {REPLAY_EVENTS.map((e) => (
          <button
            key={e.eventId}
            type="button"
            className={`dr-chip${e.eventId === eventId ? " is-on" : ""}`}
            aria-pressed={e.eventId === eventId}
            onClick={() => setEventId(e.eventId)}
          >
            {EVENT_META[e.eventId].short} · {e.eventId}
          </button>
        ))}
      </div>
      {days.length === 0 ? (
        <p className="note">The loaded rows hold no readings inside this event window.</p>
      ) : (
        <>
          <div className="rehearsal__steps" role="group" aria-label="Replay day">
            <button type="button" className="button" disabled={dayIndex === 0} onClick={() => setDayIndex((i) => Math.max(0, i - 1))}>
              ← Previous day
            </button>
            <strong aria-live="polite">{state?.dayText ?? ""}</strong>
            <button
              type="button"
              className="button"
              disabled={dayIndex >= days.length - 1}
              onClick={() => setDayIndex((i) => Math.min(days.length - 1, i + 1))}
            >
              Next day →
            </button>
          </div>
          <p className="note">
            {state && state.over.length > 0
              ? `${state.over.length} of ${data.points.length} points at or above ${event.thresholdM3s} m³/s (the Watchers line) on this day.`
              : `No point at or above ${event.thresholdM3s} m³/s on this day.`}{" "}
            {data.badge}.
          </p>
          {state?.crossed ? (
            <div className="rehearsal__crossed">
              <p>
                <span className="level-chip level-chip--warning">Crossed</span> {state.crossed.name}: {crossingText(state.crossed.iso, daily)}.
              </p>
              <AssessButton
                runKey={`rehearsal:${event.eventId}:${state.crossed.iso}`}
                label="Ask the agents about this moment"
                build={() => ({
                  key: `rehearsal:${event.eventId}:${state.crossed!.iso}`,
                  question: rehearsalQuestion(state.crossed!.name, state.crossed!.iso, event.thresholdM3s, daily),
                  eventId: event.eventId,
                  replayTs: state.crossed!.iso,
                  context: {
                    role: "insurer",
                    page: "alerts",
                    event_id: event.eventId,
                    point_id: state.crossed!.pointId,
                    place: state.crossed!.name,
                    replay_date: state.crossed!.iso.slice(0, 10),
                  },
                  provider: llmProvider,
                  allowedProviders: llmProviders,
                })}
              />
            </div>
          ) : (
            <p className="note">Step forward: the agents can be asked once a point crosses the line.</p>
          )}
        </>
      )}
    </section>
  );
}

/** Insurer Alerts: the live monitor first, the rehearsal second. */
export function Alerts() {
  return (
    <div className="page-stack alerts-page">
      <LiveAlertMonitor />
      <Rehearsal />
    </div>
  );
}
