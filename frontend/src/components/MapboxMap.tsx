"use client";

import mapboxgl, { LngLatLike, Map as MapboxMapImpl, Marker } from "mapbox-gl";
import { useEffect, useMemo, useRef } from "react";
import type { HeatmapCell, LatLng } from "@/lib/types";

type MapState = {
  map: MapboxMapImpl;
  marker: Marker;
  popup: mapboxgl.Popup | null;
};

const HEATMAP_SOURCE_ID = "chitta-heatmap";
const HEATMAP_LAYER_ID = "chitta-heatmap-circles";

function toLngLatLike(v: LatLng): LngLatLike {
  return [v.longitude, v.latitude];
}

function formatMetric(v: number | null | undefined): string {
  if (v == null) return "Unavailable";
  return `${Math.round(v)}`;
}

function cellPopupHtml(cell: HeatmapCell): string {
  const m = cell.metrics;
  return `
    <div class="chitta-popup-inner">
      <div class="chitta-popup-title">${cell.label}</div>
      <div><strong>Total:</strong> ${formatMetric(m.totalSuitability)}/100</div>
      <div><strong>Wind:</strong> ${formatMetric(m.windScore)} (${cell.providerStatus.wind})</div>
      <div><strong>Terrain:</strong> ${formatMetric(m.terrainScore)} (${cell.providerStatus.elevation})</div>
      <div><strong>Access:</strong> ${formatMetric(m.accessibilityScore)}</div>
      <div><strong>Confidence:</strong> ${formatMetric(m.confidenceScore)}</div>
    </div>
  `;
}

export function MapboxMap({
  token,
  center,
  selected,
  onSelect,
  heatmapCells,
  onHeatmapCellSelect,
  selectedHeatmapCell,
}: {
  token: string | null;
  center: LatLng;
  selected: LatLng;
  onSelect: (v: LatLng) => void;
  heatmapCells?: HeatmapCell[];
  onHeatmapCellSelect?: (cell: HeatmapCell) => void;
  selectedHeatmapCell?: HeatmapCell | null;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const stateRef = useRef<MapState | null>(null);
  const onSelectRef = useRef(onSelect);
  const onHeatmapCellSelectRef = useRef(onHeatmapCellSelect);
  const heatmapCellsRef = useRef(heatmapCells);

  const canRender = useMemo(() => Boolean(token?.trim()), [token]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    onHeatmapCellSelectRef.current = onHeatmapCellSelect;
  }, [onHeatmapCellSelect]);

  useEffect(() => {
    heatmapCellsRef.current = heatmapCells;
  }, [heatmapCells]);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!canRender) return;
    if (stateRef.current) return;

    mapboxgl.accessToken = token as string;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/outdoors-v12",
      center: toLngLatLike(center),
      zoom: 6,
      attributionControl: true,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");

    const marker = new mapboxgl.Marker({ color: "#10b981" })
      .setLngLat(toLngLatLike(selected))
      .addTo(map);

    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
      className: "chitta-heatmap-popup",
    });

    map.on("click", (e) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [HEATMAP_LAYER_ID],
      });
      if (features.length > 0) {
        const idx = features[0]?.properties?.featureIndex;
        const cells = heatmapCellsRef.current;
        if (typeof idx === "number" && cells && cells[idx]) {
          onHeatmapCellSelectRef.current?.(cells[idx]);
          return;
        }
      }
      const next = { latitude: e.lngLat.lat, longitude: e.lngLat.lng };
      marker.setLngLat([next.longitude, next.latitude]);
      onSelectRef.current(next);
    });

    map.on("load", () => {
      map.addSource(HEATMAP_SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: HEATMAP_LAYER_ID,
        type: "circle",
        source: HEATMAP_SOURCE_ID,
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            8,
            8,
            12,
            18,
          ],
          "circle-color": [
            "case",
            ["==", ["get", "dataUnavailable"], true],
            "#334155",
            [
              "interpolate",
              ["linear"],
              ["get", "totalSuitability"],
              0,
              "#991b1b",
              45,
              "#b45309",
              75,
              "#047857",
              100,
              "#064e3b",
            ],
          ],
          "circle-opacity": 0.88,
          "circle-stroke-width": 2,
          "circle-stroke-color": "#0f172a",
        },
      });

      map.on("mouseenter", HEATMAP_LAYER_ID, (e) => {
        map.getCanvas().style.cursor = "pointer";
        const feature = e.features?.[0];
        const html = feature?.properties?.popupHtml;
        if (html && feature?.geometry?.type === "Point") {
          const [lng, lat] = feature.geometry.coordinates as [number, number];
          popup.setLngLat([lng, lat]).setHTML(String(html)).addTo(map);
        }
      });

      map.on("mouseleave", HEATMAP_LAYER_ID, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
    });

    stateRef.current = { map, marker, popup };

    return () => {
      map.remove();
      stateRef.current = null;
    };
  }, [canRender, token, center, selected]);

  useEffect(() => {
    const st = stateRef.current;
    if (!st) return;
    st.map.easeTo({ center: toLngLatLike(center), duration: 500 });
  }, [center]);

  useEffect(() => {
    const st = stateRef.current;
    if (!st) return;
    st.marker.setLngLat([selected.longitude, selected.latitude]);
  }, [selected]);

  useEffect(() => {
    const st = stateRef.current;
    if (!st) return;
    const map = st.map;

    const updateSource = () => {
      const source = map.getSource(HEATMAP_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
      if (!source) return;

      if (!heatmapCells?.length) {
        source.setData({ type: "FeatureCollection", features: [] });
        return;
      }

      const geojson = {
        type: "FeatureCollection" as const,
        features: heatmapCells.map((cell, featureIndex) => ({
          type: "Feature" as const,
          geometry: {
            type: "Point" as const,
            coordinates: [cell.longitude, cell.latitude],
          },
          properties: {
            totalSuitability: cell.metrics.totalSuitability ?? -1,
            dataUnavailable: Boolean(cell.dataUnavailable || cell.metrics.totalSuitability == null),
            label: cell.label,
            popupHtml: cellPopupHtml(cell),
            featureIndex,
            isSelected:
              selectedHeatmapCell &&
              selectedHeatmapCell.latitude === cell.latitude &&
              selectedHeatmapCell.longitude === cell.longitude,
          },
        })),
      };
      source.setData(geojson);
    };

    if (map.isStyleLoaded()) {
      updateSource();
    } else {
      map.once("load", updateSource);
    }
  }, [heatmapCells, selectedHeatmapCell]);

  if (!canRender) {
    return (
      <div className="chitta-card chitta-surface flex h-full w-full items-center justify-center rounded-xl p-6 text-center text-sm text-slate-600">
        Set <code className="mx-1 rounded bg-white px-1 py-0.5">NEXT_PUBLIC_MAPBOX_TOKEN</code>
        to enable the interactive map.
      </div>
    );
  }

  return (
    <div className="chitta-card relative h-full w-full overflow-hidden rounded-xl bg-white shadow-sm">
      <div ref={containerRef} className="h-full w-full" />
      {heatmapCells?.length ? (
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg bg-slate-900/90 px-3 py-2 text-xs text-slate-100 shadow-md">
          <div className="font-medium">Suitability</div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="inline-block h-2 w-8 rounded bg-red-800" /> Low
            <span className="inline-block h-2 w-8 rounded bg-amber-700" /> Mid
            <span className="inline-block h-2 w-8 rounded bg-emerald-800" /> High
            <span className="inline-block h-2 w-8 rounded bg-slate-600" /> Unavailable
          </div>
        </div>
      ) : null}
    </div>
  );
}
