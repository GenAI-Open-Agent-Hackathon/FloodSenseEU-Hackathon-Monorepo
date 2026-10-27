import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useRef } from "react";
import { GAUGE_BOUNDS, type GaugeStatus, type GaugeSummary } from "../lib/gauges";
import type { GaugeState } from "../hooks/useGaugeLevels";
import { formatHour } from "../lib/format";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';

const LEGEND: { status: GaugeStatus; label: string }[] = [
  { status: "ok", label: "Below warning" },
  { status: "near", label: "Near warning" },
  { status: "over", label: "Above warning" },
  { status: "unknown", label: "No threshold" },
];

export function MapLegend() {
  return (
    <ul className="map-legend" aria-label="Map legend">
      {LEGEND.map((item) => (
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

/** River-gauge map. Markers come only from the gauge_levels view; nothing here is sample. */
export function GaugeMap({ load, gauges }: { load: GaugeState; gauges: GaugeSummary[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const placed = useMemo(() => gauges.filter((g) => g.lat !== null && g.lon !== null), [gauges]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const map = L.map(container, { zoomSnap: 1, attributionControl: false, scrollWheelZoom: false });
    L.control
      .attribution({ prefix: '<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>' })
      .addAttribution(`${TILE_ATTRIBUTION} · Gauges: PEGELONLINE (WSV, DL-DE-Zero-2.0) via Zetaris`)
      .addTo(map);
    L.tileLayer(TILE_URL, { maxZoom: 18 }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    const fit = () =>
      map.fitBounds(
        [
          [GAUGE_BOUNDS.south, GAUGE_BOUNDS.west],
          [GAUGE_BOUNDS.north, GAUGE_BOUNDS.east],
        ],
        { padding: [12, 12] },
      );
    fit();
    mapRef.current = map;
    // The card can be laid out after the map is made; refit once it has a real size.
    const resize = new ResizeObserver(() => {
      map.invalidateSize();
      fit();
    });
    resize.observe(container);
    return () => {
      resize.disconnect();
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.clearLayers();
    for (const g of placed) {
      const circle = L.circleMarker([g.lat as number, g.lon as number], {
        radius: 7,
        className: `map-marker map-marker--${g.status}`,
        bubblingMouseEvents: false,
      });
      circle.bindTooltip(`${g.station} (${g.water}): ${Math.round(g.levelCm)} cm · ${formatHour(g.measuredAt)}`, {
        direction: "top",
        offset: [0, -6],
      });
      layer.addLayer(circle);
    }
  }, [placed]);

  const unplaced = gauges.length - placed.length;
  return (
    <div className="gauge-map">
      <div className="gauge-map__toolbar">
        <MapLegend />
        <span className={`chip ${load.state === "live" ? "chip--live" : ""}`}>
          {load.state === "live" ? "Live · via Zetaris" : load.state === "loading" ? "Loading…" : "No live readings"}
        </span>
      </div>
      <div className="gauge-map__frame">
        <div ref={containerRef} className="leaflet-map" role="region" aria-label="River gauges on the Rhine and Ahr" />
        {load.state !== "live" && load.state !== "loading" && (
          <p className="gauge-map__empty">No live gauge readings yet.</p>
        )}
      </div>
      {unplaced > 0 && (
        <p className="note">
          {unplaced} {unplaced === 1 ? "gauge has" : "gauges have"} no known position and {unplaced === 1 ? "is" : "are"} listed only.
        </p>
      )}
      <p className="note">Station positions are approximate. No warning thresholds are loaded yet, so live gauges show as “No threshold”.</p>
    </div>
  );
}

const TREND_SYMBOL = { rising: "▲", steady: "▶", falling: "▼" } as const;

export function GaugeList({ load, gauges, limit = 6 }: { load: GaugeState; gauges: GaugeSummary[]; limit?: number }) {
  if (load.state === "loading") return <p className="note">Reading gauges…</p>;
  if (gauges.length === 0) {
    return (
      <p className="note">
        No live gauge readings yet.
        {load.state === "unavailable" ? " The gauge view could not be reached." : ""}
      </p>
    );
  }
  return (
    <ul className="gauge-list">
      {gauges.slice(0, limit).map((g) => (
        <li key={`${g.station}-${g.water}`} className={`gauge gauge--${g.status}`}>
          <div className="gauge__head">
            <div>
              <strong>{g.station}</strong>
              <span className="muted small">{g.water}</span>
            </div>
            {g.trend && (
              <span className={`trend trend--${g.trend}`}>
                {TREND_SYMBOL[g.trend]} {g.trend}
              </span>
            )}
          </div>
          <div className="gauge__value">
            {Math.round(g.levelCm)}
            <small> cm</small>
          </div>
          <div className="gauge__foot muted small">
            <span>
              Warning level {g.warningLevelCm === null ? "not loaded" : `${g.warningLevelCm} cm`} · measured {formatHour(g.measuredAt)}
            </span>
            <span className="chip chip--live">Live</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
