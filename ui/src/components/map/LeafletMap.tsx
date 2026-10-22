import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";
import { mapTiles } from "../../api/client";
import type { BoundingBox, GaugeStatus } from "../../types";

/** One marker to draw. Kept independent of the data types so the map stays reusable. */
export interface MapMarker {
  id: string;
  lat: number;
  lon: number;
  status: GaugeStatus;
  /** Tooltip text, e.g. "Passau (Danube): 612 cm". */
  label: string;
  /** Sample or reconstructed data is drawn with a dashed outline. */
  isSample: boolean;
}

interface LeafletMapProps {
  bounds: BoundingBox;
  markers: readonly MapMarker[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Called once the first tiles have loaded (or failed), for the loading screen. */
  onReady?: () => void;
  ariaLabel: string;
}

const statusClass: Record<GaugeStatus, string> = {
  ok: "map-marker--ok",
  near: "map-marker--near",
  over: "map-marker--over",
  unknown: "map-marker--unknown",
};

function toLatLngBounds(b: BoundingBox): L.LatLngBoundsExpression {
  return [
    [b.south, b.west],
    [b.north, b.east],
  ];
}

/**
 * Thin React wrapper around a plain Leaflet map. React owns the props; Leaflet
 * owns the DOM inside the container. Tiles load on demand only (no prefetch).
 */
export function LeafletMap({ bounds, markers, selectedId, onSelect, onReady, ariaLabel }: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelect);
  const onReadyRef = useRef(onReady);
  onSelectRef.current = onSelect;
  onReadyRef.current = onReady;

  // Create the map once.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const map = L.map(container, { zoomSnap: 1, attributionControl: false, scrollWheelZoom: false });
    const report = mapTiles.reportIssueUrl
      ? ` · <a href="${mapTiles.reportIssueUrl}" target="_blank" rel="noopener">Report a map issue</a>`
      : "";
    L.control
      .attribution({ prefix: '<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>' })
      .addAttribution(`${mapTiles.attributionHtml}${report}`)
      .addTo(map);
    const tiles = L.tileLayer(mapTiles.url, { maxZoom: mapTiles.maxZoom });
    tiles.once("load tileerror", () => onReadyRef.current?.());
    tiles.addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  // Fit the view whenever the region changes.
  useEffect(() => {
    mapRef.current?.fitBounds(toLatLngBounds(bounds), { padding: [12, 12] });
  }, [bounds.south, bounds.west, bounds.north, bounds.east]);

  // Redraw markers when data or selection changes.
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) {
      return;
    }
    layer.clearLayers();
    // Draw the most severe last so it stays on top.
    const order: GaugeStatus[] = ["unknown", "ok", "near", "over"];
    const sorted = [...markers].sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status));
    for (const marker of sorted) {
      const selected = marker.id === selectedId;
      const circle = L.circleMarker([marker.lat, marker.lon], {
        radius: selected ? 10 : 7,
        className: ["map-marker", statusClass[marker.status], marker.isSample ? "map-marker--sample" : "", selected ? "is-selected" : ""].join(" "),
        bubblingMouseEvents: false,
      });
      circle.bindTooltip(marker.label, { direction: "top", offset: [0, -6] });
      circle.on("click", () => onSelectRef.current(marker.id));
      layer.addLayer(circle);
    }
  }, [markers, selectedId]);

  return <div ref={containerRef} className="leaflet-map" role="region" aria-label={ariaLabel} />;
}
