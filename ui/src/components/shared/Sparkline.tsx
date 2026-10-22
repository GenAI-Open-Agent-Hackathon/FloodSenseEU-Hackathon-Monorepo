interface SparklineProps {
  values: readonly number[];
  /** Optional horizontal reference line, e.g. a warning threshold. */
  threshold?: number;
  width?: number;
  height?: number;
  label: string;
}

/** Dependency-free SVG line chart for short series. */
export function Sparkline({ values, threshold, width = 140, height = 40, label }: SparklineProps) {
  if (values.length < 2) {
    return null;
  }
  const all = threshold === undefined ? values : [...values, threshold];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const x = (i: number) => (i / (values.length - 1)) * width;
  const y = (v: number) => height - 3 - ((v - min) / span) * (height - 6);
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label={label}>
      {threshold !== undefined && <line x1={0} x2={width} y1={y(threshold)} y2={y(threshold)} className="sparkline__threshold" />}
      <polyline points={points} className="sparkline__line" />
      <circle cx={x(values.length - 1)} cy={y(values[values.length - 1] ?? 0)} r={3} className="sparkline__dot" />
    </svg>
  );
}
