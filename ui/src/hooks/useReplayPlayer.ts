import { useCallback, useEffect, useState } from "react";

export const replaySpeeds = [1, 2, 4, 8] as const;
export type ReplaySpeed = (typeof replaySpeeds)[number];

export interface ReplayPlayer {
  hour: number;
  playing: boolean;
  speed: ReplaySpeed;
  setHour: (hour: number) => void;
  togglePlay: () => void;
  setSpeed: (speed: ReplaySpeed) => void;
}

/** Plays through `hours` steps; speed is replayed hours per second. */
export function useReplayPlayer(hours: number, resetKey: string): ReplayPlayer {
  const [hour, setHourState] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>(2);
  const lastHour = Math.max(0, hours - 1);

  useEffect(() => {
    setHourState(0);
    setPlaying(false);
  }, [resetKey]);

  useEffect(() => {
    if (!playing) {
      return;
    }
    // Stop here, not inside the setHour updater. Updaters must be pure, and
    // Strict Mode runs them twice.
    if (hour >= lastHour) {
      setPlaying(false);
      return;
    }
    const timer = window.setInterval(() => {
      setHourState((h) => (h >= lastHour ? h : h + 1));
    }, 1000 / speed);
    return () => window.clearInterval(timer);
  }, [playing, speed, lastHour, hour]);

  const setHour = useCallback((next: number) => setHourState(Math.min(lastHour, Math.max(0, next))), [lastHour]);

  const togglePlay = useCallback(() => {
    if (!playing && hour >= lastHour) {
      setHourState(0); // restart from the beginning
    }
    setPlaying(!playing);
  }, [playing, hour, lastHour]);

  return { hour, playing, speed, setHour, togglePlay, setSpeed };
}
