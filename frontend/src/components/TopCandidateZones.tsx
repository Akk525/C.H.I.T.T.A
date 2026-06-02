"use client";

import type { HeatmapCell } from "@/lib/types";

function formatMetric(v: number | null | undefined) {
  if (v == null) return "Unavailable";
  return `${Math.max(0, Math.min(100, Math.round(v)))}`;
}

export function TopCandidateZones({
  cells,
  onSelect,
  selected,
}: {
  cells: HeatmapCell[];
  onSelect?: (cell: HeatmapCell) => void;
  selected?: HeatmapCell | null;
}) {
  if (!cells.length) return null;

  return (
    <div className="chitta-card rounded-xl bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold tracking-wide text-slate-900">
        Top Candidate Zones
      </h3>
      <div className="mt-3 grid gap-2">
        {cells.map((cell, idx) => {
          const isSelected =
            selected &&
            selected.latitude === cell.latitude &&
            selected.longitude === cell.longitude;
          const total = cell.metrics.totalSuitability;
          return (
            <button
              key={`${cell.latitude}-${cell.longitude}-${idx}`}
              type="button"
              onClick={() => onSelect?.(cell)}
              className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                isSelected
                  ? "border-emerald-300 bg-emerald-50"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-900">
                  #{idx + 1} · {cell.label}
                </div>
                <div className={`text-sm font-semibold ${total == null ? "text-slate-500" : "text-emerald-700"}`}>
                  {total == null ? "Unavailable" : `${formatMetric(total)}/100`}
                </div>
              </div>
              <div className="mt-1 text-xs text-slate-600">
                {cell.latitude.toFixed(4)}, {cell.longitude.toFixed(4)} · Wind{" "}
                {cell.providerStatus.wind} · Elev {cell.providerStatus.elevation}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
