import { useEffect, useMemo, useState } from "react";
import { useConsole } from "../context/ConsoleContext";
import ahr from "../fixtures/ahr_2021.json";
import {
  buildFrames,
  clampStep,
  crossings,
  dayStarts,
  isoOf,
  momentQuestion,
  momentText,
  nextStep,
  readingsAt,
  REPLAY_EVENTS,
  replayLabel,
  type DisasterEvent,
  type ReplayPoint,
  type ReplayReading,
} from "../lib/disasterReplay";

const PLAY_MS = 220;

interface EventData {
  rows: ReplayReading[];
  points: ReplayPoint[];
  source: string;
}

/** Disaster replay: scrub through Ahr 2021 or Valencia 2024 hour by hour. Never live. */
export function DisasterReplay() {
  const desk = useConsole();
  const [eventId, setEventId] = useState<DisasterEvent["eventId"]>("EMSR517");
  const event = REPLAY_EVENTS.find((e) => e.eventId === eventId) ?? REPLAY_EVENTS[0];

  const data = useMemo<EventData>(() => {
    if (event.eventId === "EMSR517") {
      return { rows: ahr.hazard_timeline as ReplayReading[], points: ahr.points, source: ahr._source };
    }
    return {
      rows: desk.hazard.rows,
      points: desk.points.map((p) => ({ point_id: p.point_id, name: `${p.name}` })),
      source: `hazard_timeline view (${desk.hazard.origin}): ERA5 hourly rain, GloFAS daily discharge. ${desk.hazard.detail}`,
    };
  }, [event.eventId, desk.hazard, desk.points]);

  const frames = useMemo(() => buildFrames(data.rows, event), [data.rows, event]);
  const days = useMemo(() => dayStarts(frames), [frames]);
  const turned = useMemo(() => crossings(data.rows, frames, event.thresholdM3s), [data.rows, frames, event.thresholdM3s]);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [pointId, setPointId] = useState<string>(data.points[0]?.point_id ?? "");

  // A new event starts at its first crossing, or its first hour.
  useEffect(() => {
    setPlaying(false);
    const first = [...turned.values()].sort((a, b) => a.index - b.index)[0];
    setStep(first ? Math.max(0, first.index - 6) : 0);
    setPointId(first ? [...turned.entries()].find(([, c]) => c === first)?.[0] ?? "" : data.points[0]?.point_id ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.eventId, frames.length]);

  useEffect(() => {
    if (!playing || frames.length === 0) return;
    const t = window.setInterval(() => setStep((s) => nextStep(s, frames.length)), PLAY_MS);
    return () => window.clearInterval(t);
  }, [playing, frames.length]);

  const at = clampStep(step, frames.length);
  const iso = frames[at] ?? null;
  const now = useMemo(() => (iso ? readingsAt(data.rows, iso) : new Map()), [data.rows, iso]);
  const point = data.points.find((p) => p.point_id === pointId) ?? data.points[0];
  const series = useMemo(() => {
    const pts = data.rows.filter((r) => r.point_id === point?.point_id);
    const byIso = new Map(pts.map((r) => [isoOf(r.ts_utc), r]));
    return frames.map((f) => byIso.get(f) ?? null);
  }, [data.rows, frames, point?.point_id]);

  const ask = () => {
    if (!iso || !point) return;
    desk.openAsk(momentQuestion(point.name, iso), {
      page: "replay",
      event_id: event.eventId,
      replay_date: iso,
      point_id: point.point_id,
      place: point.name,
    });
  };

  return (
    <section className="card dr" aria-label="Disaster replay">
      <div className="dr-head">
        <div>
          <p className="section-label">Disaster replay</p>
          <h2 className="dr-title">{event.name}</h2>
        </div>
        <p className="dr-badge" role="status">
          {replayLabel(event)}
        </p>
      </div>
      <div className="dr-events" role="group" aria-label="Event">
        {REPLAY_EVENTS.map((e) => (
          <button
            key={e.eventId}
            type="button"
            className={`dr-chip${e.eventId === eventId ? " is-on" : ""}`}
            aria-pressed={e.eventId === eventId}
            onClick={() => setEventId(e.eventId)}
          >
            {e.name} · {e.eventId}
          </button>
        ))}
      </div>

      {frames.length === 0 ? (
        <p className="note">No readings for this window in the loaded rows.</p>
      ) : (
        <>
          <div className="dr-controls">
            <button type="button" className="dr-play" onClick={() => setPlaying((p) => !p)} aria-pressed={playing}>
              {playing ? "Pause" : "Play"}
            </button>
            <button type="button" className="dr-chip" onClick={() => setStep((s) => clampStep(s - 1, frames.length))} aria-label="One hour back">
              −1 h
            </button>
            <button type="button" className="dr-chip" onClick={() => setStep((s) => clampStep(s + 1, frames.length))} aria-label="One hour on">
              +1 h
            </button>
            {days.map((d) => (
              <button key={d.day} type="button" className={`dr-chip${iso?.startsWith(d.day) ? " is-on" : ""}`} onClick={() => setStep(d.index)}>
                {momentText(`${d.day}T00:00:00Z`).replace(/ at .*/, "")}
              </button>
            ))}
          </div>
          <div className="dr-scrub">
            <input
              type="range"
              min={0}
              max={frames.length - 1}
              value={at}
              onChange={(e) => {
                setPlaying(false);
                setStep(Number(e.target.value));
              }}
              aria-label="Replay time"
              aria-valuetext={iso ? momentText(iso) : ""}
            />
            <div className="dr-ticks" aria-hidden="true">
              {[...turned.entries()].map(([pid, c]) => (
                <span
                  key={pid}
                  className="dr-tick"
                  style={{ left: `${(c.index / Math.max(1, frames.length - 1)) * 100}%` }}
                  title={`${data.points.find((p) => p.point_id === pid)?.name ?? pid} turned`}
                />
              ))}
            </div>
          </div>
          <p className="dr-now" aria-live="polite">
            <strong>{iso ? `${momentText(iso)} UTC` : ""}</strong> · hour {at + 1} of {frames.length}
          </p>

          <ReplayChart series={series} cursor={at} threshold={event.thresholdM3s} turnedAt={turned.get(point?.point_id ?? "")?.index ?? null} />

          <table className="dr-table">
            <thead>
              <tr>
                <th scope="col">Place</th>
                <th scope="col">Rain (mm/h)</th>
                <th scope="col">Discharge (m³/s)</th>
                <th scope="col">State</th>
              </tr>
            </thead>
            <tbody>
              {data.points.map((p) => {
                const r = now.get(p.point_id);
                const c = turned.get(p.point_id);
                const above = r?.discharge_m3s != null && r.discharge_m3s >= event.thresholdM3s;
                const here = c && c.index === at;
                return (
                  <tr
                    key={p.point_id}
                    className={`${p.point_id === point?.point_id ? "is-sel " : ""}${above ? "is-above" : ""}${here ? " is-turn" : ""}`}
                    onClick={() => setPointId(p.point_id)}
                  >
                    <th scope="row">
                      <button type="button" className="dr-link" onClick={() => setPointId(p.point_id)}>
                        {p.name}
                      </button>
                    </th>
                    <td>{r ? r.rain_mm.toFixed(1) : "—"}</td>
                    <td>{r?.discharge_m3s != null ? r.discharge_m3s.toFixed(1) : "—"}</td>
                    <td>
                      {here ? (
                        <strong className="dr-turn">The moment it turned</strong>
                      ) : above ? (
                        "Above the line"
                      ) : c && c.index > at ? (
                        `Turns ${momentText(c.iso)}`
                      ) : (
                        "Below the line"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="button-row">
            <button type="button" className="dr-ask" onClick={ask} disabled={!point || !iso}>
              Ask the agents about this moment
            </button>
          </div>
          <p className="note">
            Line: {event.thresholdM3s} m³/s, the Watchers anomaly line. Discharge is the modelled GloFAS daily value for that
            day; rain is hourly. {data.source}
          </p>
        </>
      )}
    </section>
  );
}

/** Rain bars and discharge line for the selected place, with the line, the cursor and the turning point. */
function ReplayChart({
  series,
  cursor,
  threshold,
  turnedAt,
}: {
  series: (ReplayReading | null)[];
  cursor: number;
  threshold: number;
  turnedAt: number | null;
}) {
  const W = 640;
  const H = 150;
  const n = Math.max(1, series.length);
  const maxQ = Math.max(threshold * 1.2, ...series.map((r) => r?.discharge_m3s ?? 0));
  const maxR = Math.max(5, ...series.map((r) => r?.rain_mm ?? 0));
  const x = (i: number) => (i / Math.max(1, n - 1)) * W;
  const yQ = (v: number) => H - (v / maxQ) * (H - 10);
  const line = series
    .map((r, i) => (r?.discharge_m3s != null ? `${x(i).toFixed(1)},${yQ(r.discharge_m3s).toFixed(1)}` : null))
    .filter(Boolean)
    .join(" ");
  return (
    <svg className="dr-chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Rain and discharge over the event">
      {series.map((r, i) =>
        r && r.rain_mm > 0 ? (
          <rect key={i} className="dr-rain" x={x(i) - W / n / 2} width={Math.max(1, W / n - 0.5)} y={0} height={(r.rain_mm / maxR) * (H * 0.45)} />
        ) : null,
      )}
      <line className="dr-thr" x1={0} x2={W} y1={yQ(threshold)} y2={yQ(threshold)} />
      <polyline className="dr-q" points={line} fill="none" />
      {turnedAt !== null && <circle className="dr-turnpt" cx={x(turnedAt)} cy={yQ(series[turnedAt]?.discharge_m3s ?? threshold)} r={5} />}
      <line className="dr-cursor" x1={x(cursor)} x2={x(cursor)} y1={0} y2={H} />
    </svg>
  );
}
