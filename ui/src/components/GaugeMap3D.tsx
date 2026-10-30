import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "../styles/map3d.css";
import { useEffect, useRef } from "react";
import { GAUGE_BOUNDS, type GaugeSummary } from "../lib/gauges";
maplibregl.setWorkerUrl(workerUrl);

// Duplicated from GaugeMap.tsx to avoid a circular import.
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';
const DEM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";

// Same tokens as .map-marker--* in global.css, resolved at runtime so themes apply.
const STATUS_VAR = { ok: "--risk-low", near: "--risk-moderate", over: "--warn-ink", unknown: "--gauge-unknown" } as const;

function statusColors(): Record<string, string> {
  const css = getComputedStyle(document.documentElement);
  return Object.fromEntries(Object.entries(STATUS_VAR).map(([k, v]) => [k, css.getPropertyValue(v).trim() || "#888"]));
}

function toGeoJSON(gauges: GaugeSummary[], colors: Record<string, string>): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: gauges
      .filter((g) => g.lat !== null && g.lon !== null)
      .map((g) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [g.lon as number, g.lat as number] },
        properties: { color: colors[g.status] ?? colors.unknown, text: `${g.station} (${g.water}): ${Math.round(g.levelCm)} cm` },
      })),
  };
}

export function GaugeMap3D({ gauges }: { gauges: GaugeSummary[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const latest = useRef(gauges);
  latest.current = gauges;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const map = new maplibregl.Map({
      container,
      style: {
        version: 8,
        sources: {
          osm: { type: "raster", tiles: [TILE_URL], tileSize: 256, maxzoom: 18, attribution: TILE_ATTRIBUTION },
          dem: {
            type: "raster-dem",
            tiles: [DEM_URL],
            encoding: "terrarium",
            tileSize: 256,
            maxzoom: 15,
            attribution: "Terrain: Mapzen / AWS Terrain Tiles",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      bounds: [
        [GAUGE_BOUNDS.west, GAUGE_BOUNDS.south],
        [GAUGE_BOUNDS.east, GAUGE_BOUNDS.north],
      ],
      fitBoundsOptions: { padding: 12, pitch: 60, bearing: -20 },
      pitch: 60,
      bearing: -20,
      maxPitch: 80,
      cooperativeGestures: true,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    map.on("load", () => {
      map.setTerrain({ source: "dem", exaggeration: 1.6 });
      map.addSource("gauges", { type: "geojson", data: toGeoJSON(latest.current, statusColors()) });
      map.addLayer({
        id: "gauges",
        type: "circle",
        source: "gauges",
        paint: { "circle-radius": 7, "circle-color": ["get", "color"], "circle-stroke-width": 2, "circle-stroke-color": "#fff" },
      });
      map.on("mousemove", "gauges", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setText(String(f.properties?.text))
          .addTo(map);
      });
      map.on("mouseleave", "gauges", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
    });
    return () => {
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const src = mapRef.current?.getSource("gauges") as maplibregl.GeoJSONSource | undefined;
    src?.setData(toGeoJSON(gauges, statusColors()));
  }, [gauges]);

  return <div ref={containerRef} className="map3d" role="region" aria-label="River gauges (3D)" />;
}

export default GaugeMap3D;
