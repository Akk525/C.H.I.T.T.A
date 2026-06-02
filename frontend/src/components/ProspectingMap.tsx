"use client";

import mapboxgl from "mapbox-gl";
import { useEffect, useRef } from "react";
import type { LatLng, ProspectingCandidate } from "@/lib/types";

const SOURCE_ID = "prospecting-candidates";
const LAYER_ID = "prospecting-circles";
const LAYER_SELECTED = "prospecting-selected";

function candidateColor(c: ProspectingCandidate): string {
  if (c.totalSuitability === null) return "#94a3b8";
  if (c.totalSuitability >= 70) return "#059669";
  if (c.totalSuitability >= 55) return "#0284c7";
  if (c.totalSuitability >= 40) return "#d97706";
  return "#e11d48";
}

function popupHtml(c: ProspectingCandidate): string {
  const score = c.totalSuitability != null ? `${c.totalSuitability}/100` : "Unavailable";
  const decision = c.finalDecision ? ` · ${c.finalDecision}` : "";
  const wind = c.windScore != null ? `${c.windScore}` : "–";
  const terrain = c.terrainScore != null ? `${c.terrainScore}` : "–";
  return `
    <div style="font-size:12px;line-height:1.6;min-width:140px">
      <div style="font-weight:600;margin-bottom:4px">${score}${decision}</div>
      <div>Wind: ${wind} · Terrain: ${terrain}</div>
      <div style="color:#64748b;font-size:10px">${c.latitude.toFixed(4)}, ${c.longitude.toFixed(4)}</div>
    </div>
  `;
}

function buildGeoJson(
  candidates: ProspectingCandidate[],
  selectedId: string | null,
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: candidates.map((c) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [c.longitude, c.latitude] },
      properties: {
        id: c.id,
        score: c.totalSuitability ?? -1,
        color: candidateColor(c),
        selected: c.id === selectedId,
        enriched: c.isFullyEnriched,
      },
    })),
  };
}

export function ProspectingMap({
  token,
  center,
  candidates,
  selectedId,
  onSelect,
}: {
  token: string | null;
  center: LatLng;
  candidates: ProspectingCandidate[];
  selectedId: string | null;
  onSelect: (c: ProspectingCandidate) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);

  // Init map
  useEffect(() => {
    if (!token || !containerRef.current || mapRef.current) return;
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/outdoors-v12",
      center: [center.longitude, center.latitude],
      zoom: 7,
    });
    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Fly to center when it changes
  useEffect(() => {
    mapRef.current?.flyTo({ center: [center.longitude, center.latitude], zoom: 7 });
  }, [center.latitude, center.longitude]);

  // Update candidate layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const update = () => {
      const geojson = buildGeoJson(candidates, selectedId);

      if (!map.getSource(SOURCE_ID)) {
        map.addSource(SOURCE_ID, { type: "geojson", data: geojson });

        // All candidates layer
        map.addLayer({
          id: LAYER_ID,
          type: "circle",
          source: SOURCE_ID,
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["get", "score"], -1, 6, 0, 7, 50, 9, 100, 11],
            "circle-color": ["get", "color"],
            "circle-opacity": 0.85,
            "circle-stroke-width": ["case", ["get", "enriched"], 2, 0],
            "circle-stroke-color": "#ffffff",
          },
        });

        // Selected ring
        map.addLayer({
          id: LAYER_SELECTED,
          type: "circle",
          source: SOURCE_ID,
          filter: ["==", ["get", "selected"], true],
          paint: {
            "circle-radius": 16,
            "circle-color": "transparent",
            "circle-stroke-width": 3,
            "circle-stroke-color": "#0f172a",
          },
        });

        // Click handler
        map.on("click", LAYER_ID, (e) => {
          if (!e.features?.length) return;
          const id = e.features[0].properties?.id as string;
          const cand = candidates.find((c) => c.id === id);
          if (cand) onSelect(cand);

          const coords = (e.features[0].geometry as GeoJSON.Point).coordinates as [number, number];
          popupRef.current?.remove();
          popupRef.current = new mapboxgl.Popup({ offset: 12, closeButton: false })
            .setLngLat(coords)
            .setHTML(popupHtml(cand!))
            .addTo(map);
        });
        map.on("mouseenter", LAYER_ID, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", LAYER_ID, () => { map.getCanvas().style.cursor = ""; });
      } else {
        (map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource).setData(geojson);
      }
    };

    if (map.isStyleLoaded()) {
      update();
    } else {
      map.once("load", update);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidates, selectedId]);

  if (!token) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-100 text-sm text-slate-500">
        Mapbox token required for map display.
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full rounded-xl overflow-hidden" />
      {/* Legend */}
      <div className="absolute bottom-3 left-3 rounded-lg bg-white/90 px-3 py-2 text-[10px] shadow backdrop-blur">
        <div className="font-semibold text-slate-700 mb-1">Suitability</div>
        {[
          { color: "#059669", label: "≥70 Promising" },
          { color: "#0284c7", label: "55–70 Mixed" },
          { color: "#d97706", label: "40–55 Caution" },
          { color: "#e11d48", label: "<40 Poor" },
          { color: "#94a3b8", label: "No data" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            <span className="text-slate-600">{label}</span>
          </div>
        ))}
        <div className="mt-1 border-t border-slate-200 pt-1 text-slate-400">
          White ring = fully enriched
        </div>
      </div>
    </div>
  );
}
