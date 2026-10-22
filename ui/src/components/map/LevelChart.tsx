import type { ForecastPoint, GaugeThresholds, LevelPoint } from "../../types";

interface LevelChartProps {
  observed: readonly LevelPoint[];
  forecast?: readonly ForecastPoint[];
  thresholds: GaugeThresholds | null;
  /** Accessible summary of the chart. */
  title: string;
  /** Optional fixed time range, e.g. the full replay window, so the x axis does not jump. */
  timeRange?: { start: string; end: string };
}

const W = 420;
const H = 210;
const PAD = { top: 22, right: 12, bottom: 26, left: 44 };

function formatHour(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Water-level chart: observed line, threshold lines and an optional forecast band. */
export function LevelChart({ observed, forecast = [], thresholds, title, timeRange }: LevelChartProps) {
  const times = [...observed.map((p) => Date.parse(p.t)), ...forecast.map((p) => Date.parse(p.t))];
  if (times.length === 0) {
    return <p className="muted">No measurements available for this gauge.</p>;
  }
  const t0 = timeRange ? Date.parse(timeRange.start) : Math.min(...times);
  const t1 = timeRange ? Date.parse(timeRange.end) : Math.max(...times);
  const levels = [
    ...observed.map((p) => p.cm),
    ...forecast.flatMap((p) => [p.lowCm, p.highCm]),
    ...(thresholds ? [thresholds.warningCm, thresholds.nearCm] : []),
  ];
  const rawMin = Math.min(...levels);
  const rawMax = Math.max(...levels);
  const margin = Math.max(10, (rawMax - rawMin) * 0.1);
  const yMin = Math.floor((rawMin - margin) / 10) * 10;
  const yMax = Math.ceil((rawMax + margin) / 10) * 10;

  const x = (t: number) => PAD.left + ((t - t0) / Math.max(1, t1 - t0)) * (W - PAD.left - PAD.right);
  const y = (cm: number) => PAD.top + (1 - (cm - yMin) / Math.max(1, yMax - yMin)) * (H - PAD.top - PAD.bottom);
  const path = (pts: [number, number][]) => pts.map(([px, py], i) => `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`).join(" ");

  const observedPath = path(observed.map((p) => [x(Date.parse(p.t)), y(p.cm)]));
  const bandPath =
    forecast.length > 0
      ? `${path(forecast.map((p) => [x(Date.parse(p.t)), y(p.highCm)]))} ${[...forecast]
          .reverse()
          .map((p) => `L${x(Date.parse(p.t)).toFixed(1)},${y(p.lowCm).toFixed(1)}`)
          .join(" ")} Z`
      : "";
  const midPath = forecast.length > 0 ? path(forecast.map((p) => [x(Date.parse(p.t)), y(p.midCm)])) : "";
  const last = observed[observed.length - 1];
  const yTicks = [yMin, Math.round((yMin + yMax) / 2), yMax];

  return (
    <figure className="level-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
        {yTicks.map((tick) => (
          <g key={tick}>
            <line className="level-chart__grid" x1={PAD.left} x2={W - PAD.right} y1={y(tick)} y2={y(tick)} />
            <text className="level-chart__axis" x={PAD.left - 6} y={y(tick) + 4} textAnchor="end">
              {tick}
            </text>
          </g>
        ))}
        <text className="level-chart__axis" x={PAD.left} y={H - 8}>
          {formatHour(new Date(t0).toISOString())}
        </text>
        <text className="level-chart__axis" x={W - PAD.right} y={H - 8} textAnchor="end">
          {formatHour(new Date(t1).toISOString())}
        </text>

        {bandPath && <path className="level-chart__band" d={bandPath} />}
        {midPath && <path className="level-chart__forecast" d={midPath} />}

        {thresholds && (
          <>
            <line className="level-chart__threshold level-chart__threshold--near" x1={PAD.left} x2={W - PAD.right} y1={y(thresholds.nearCm)} y2={y(thresholds.nearCm)} />
            <line className="level-chart__threshold level-chart__threshold--warning" x1={PAD.left} x2={W - PAD.right} y1={y(thresholds.warningCm)} y2={y(thresholds.warningCm)} />
            <text className="level-chart__threshold-label level-chart__threshold-label--warning" x={W - PAD.right - 4} y={y(thresholds.warningCm) - 4} textAnchor="end">
              Red from {thresholds.warningCm} cm
            </text>
          </>
        )}

        {observed.length > 1 && <path className="level-chart__line" d={observedPath} />}
        {last && (
          <>
            <line className="level-chart__now" x1={x(Date.parse(last.t))} x2={x(Date.parse(last.t))} y1={PAD.top} y2={H - PAD.bottom} />
            <circle className="level-chart__dot" cx={x(Date.parse(last.t))} cy={y(last.cm)} r={4} />
          </>
        )}
        <text className="level-chart__axis" x={8} y={12}>
          cm
        </text>
      </svg>
      <figcaption className="level-chart__legend">
        <span className="level-chart__key level-chart__key--observed">Observed</span>
        {forecast.length > 0 && <span className="level-chart__key level-chart__key--band">Forecast band (sample model)</span>}
        {thresholds && <span className="level-chart__key level-chart__key--warning">{thresholds.label}</span>}
        {thresholds && <span className="level-chart__key level-chart__key--near">Amber from {thresholds.nearCm} cm</span>}
      </figcaption>
    </figure>
  );
}
