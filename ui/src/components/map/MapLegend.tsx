import type { GaugeStatus } from "../../types";

const items: { status: GaugeStatus; label: string }[] = [
  { status: "ok", label: "Below warning" },
  { status: "near", label: "Near warning" },
  { status: "over", label: "Above warning" },
  { status: "unknown", label: "No threshold" },
];

export function MapLegend() {
  return (
    <ul className="map-legend" aria-label="Map legend">
      {items.map((item) => (
        <li key={item.status}>
          <span className={`map-legend__dot map-legend__dot--${item.status}`} aria-hidden="true" />
          {item.label}
        </li>
      ))}
      <li>
        <span className="map-legend__dot map-legend__dot--sample" aria-hidden="true" />
        Dashed outline = sample data
      </li>
    </ul>
  );
}
