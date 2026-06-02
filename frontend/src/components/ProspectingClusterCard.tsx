"use client";

import type { ProspectingCluster } from "@/lib/types";

const DECISION_COLOURS: Record<string, string> = {
  promising: "bg-emerald-100 text-emerald-800",
  mixed: "bg-blue-100 text-blue-800",
  caution: "bg-amber-100 text-amber-800",
  poor: "bg-rose-100 text-rose-800",
  unknown: "bg-slate-100 text-slate-600",
};

export function ProspectingClusterCard({
  cluster,
  onFocus,
}: {
  cluster: ProspectingCluster;
  onFocus: (cluster: ProspectingCluster) => void;
}) {
  const decisionCls = DECISION_COLOURS[cluster.topDecision] ?? DECISION_COLOURS.unknown;
  const scoreColour =
    cluster.averageSuitability >= 70
      ? "text-emerald-700"
      : cluster.averageSuitability >= 55
        ? "text-blue-700"
        : cluster.averageSuitability >= 40
          ? "text-amber-700"
          : "text-rose-700";

  return (
    <button
      type="button"
      onClick={() => onFocus(cluster)}
      className="chitta-card flex flex-col gap-1.5 rounded-xl bg-white p-4 shadow-sm text-left transition-colors hover:bg-slate-50 w-full"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-semibold text-slate-900">{cluster.label}</div>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${decisionCls}`}>
          {cluster.topDecision}
        </span>
      </div>
      <div className={`text-2xl font-bold ${scoreColour}`}>
        {cluster.averageSuitability.toFixed(0)}<span className="text-sm font-normal text-slate-400">/100</span>
      </div>
      <div className="text-xs text-slate-500">
        {cluster.candidateCount} candidate{cluster.candidateCount !== 1 ? "s" : ""} ·{" "}
        {cluster.centroidLatitude.toFixed(2)}°N, {cluster.centroidLongitude.toFixed(2)}°E
      </div>
      <div className="text-[11px] text-slate-600 leading-5">{cluster.summary}</div>
    </button>
  );
}
