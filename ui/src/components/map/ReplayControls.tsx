import { replaySpeeds, type ReplayPlayer } from "../../hooks/useReplayPlayer";
import type { ReplayScenario } from "../../types";

interface ReplayControlsProps {
  scenario: ReplayScenario;
  player: ReplayPlayer;
}

export function replayHourTime(scenario: ReplayScenario, hour: number): Date {
  return new Date(Date.parse(scenario.startAt) + hour * 3_600_000);
}

/** Play/pause, speed and an hour slider for a replay scenario. */
export function ReplayControls({ scenario, player }: ReplayControlsProps) {
  const time = replayHourTime(scenario, player.hour);
  const milestone = [...scenario.milestones].reverse().find((m) => m.hour <= player.hour);

  return (
    <div className="replay">
      <div className="replay__row">
        <button type="button" className="button button--primary replay__play" onClick={player.togglePlay} aria-pressed={player.playing}>
          {player.playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <label className="replay__slider">
          <span className="sr-only">Replay hour</span>
          <input
            type="range"
            min={0}
            max={scenario.hours - 1}
            step={1}
            value={player.hour}
            onChange={(event) => player.setHour(Number(event.target.value))}
            aria-valuetext={time.toUTCString()}
          />
        </label>
        <div className="segmented segmented--small" role="radiogroup" aria-label="Replay speed">
          {replaySpeeds.map((speed) => (
            <button
              key={speed}
              type="button"
              role="radio"
              aria-checked={player.speed === speed}
              className={`segmented__option ${player.speed === speed ? "is-active" : ""}`}
              onClick={() => player.setSpeed(speed)}
            >
              {speed}×
            </button>
          ))}
        </div>
      </div>
      <div className="replay__row replay__row--meta">
        <strong className="replay__time">
          Hour {player.hour + 1}/{scenario.hours} ·{" "}
          {time.toLocaleString("en-GB", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })} UTC
        </strong>
        {milestone && <span className="replay__milestone">{milestone.label}</span>}
      </div>
    </div>
  );
}
