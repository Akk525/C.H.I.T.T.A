"use client";

import { useState } from "react";
import type { EvidenceQuality, EvidenceQualityItem, EvidenceQualityReport } from "@/lib/types";

type Props = {
  report: EvidenceQualityReport;
};

function qualityBadge(q: EvidenceQuality) {
  switch (q) {
    case "high":   return "bg-emerald-100 text-emerald-800";
    case "medium": return "bg-amber-100 text-amber-800";
    case "low":    return "bg-rose-100 text-rose-800";
  }
}

function overallBadge(q: EvidenceQuality) {
  switch (q) {
    case "high":   return { bg: "bg-emerald-50", border: "border-emerald-200", badge: "bg-emerald-700 text-white" };
    case "medium": return { bg: "bg-amber-50", border: "border-amber-200", badge: "bg-amber-600 text-white" };
    case "low":    return { bg: "bg-rose-50", border: "border-rose-200", badge: "bg-rose-700 text-white" };
  }
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 45 ? "bg-amber-400" : "bg-rose-500";
  return (
    <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function DimensionCard({ item }: { item: EvidenceQualityItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="chitta-panel rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full p-3 text-left hover:bg-[var(--chitta-surface)] transition-colors"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-xs font-bold text-[var(--chitta-ink)]">{item.dimension}</span>
              <span
                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${qualityBadge(item.quality)}`}
              >
                {item.quality}
              </span>
            </div>
            <p className="text-[10px] text-[var(--chitta-muted)] leading-snug line-clamp-1">{item.source}</p>
            <ConfidenceBar value={item.confidence} />
            <p className="mt-1 text-[10px] text-[var(--chitta-muted)]">
              Confidence: <span className="chitta-mono font-semibold">{item.confidence.toFixed(0)}/100</span>
            </p>
          </div>
          <span className="shrink-0 text-[10px] text-[var(--chitta-muted)] mt-0.5">
            {expanded ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-[var(--chitta-border)] px-3 pb-3 pt-2 space-y-2 bg-[var(--chitta-surface)]">
          <p className="text-[10px] text-slate-500 break-words">{item.source}</p>
          {item.limitations.length > 0 && (
            <ul className="space-y-0.5">
              {item.limitations.map((lim, i) => (
                <li key={i} className="text-[11px] text-slate-600 flex gap-1.5">
                  <span className="text-[var(--chitta-muted)] shrink-0">•</span>
                  <span>{lim}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="rounded bg-amber-50 border border-amber-200 px-2.5 py-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-700 mb-0.5">
              Potential error
            </p>
            <p className="text-[11px] text-amber-800">{item.potentialError}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export function EvidenceQualityPanel({ report }: Props) {
  const colors = overallBadge(report.overallQuality);

  return (
    <div className="space-y-3">
      <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--chitta-ink)]">
        Evidence Quality Assessment
      </h2>

      {/* Overall banner */}
      <div className={`rounded-lg border p-3 ${colors.bg} ${colors.border}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className={`rounded-md px-2 py-0.5 text-xs font-bold tracking-wider uppercase ${colors.badge}`}>
            {report.overallQuality}
          </span>
          <span className="text-xs font-semibold text-slate-500">Overall data quality</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-600">
            Data confidence:&nbsp;
            <span className="chitta-mono font-bold text-[var(--chitta-ink)]">
              {report.overallConfidence.toFixed(0)}/100
            </span>
          </span>
          <div className="flex-1 h-1.5 rounded-full bg-white/60 overflow-hidden">
            <div
              className="h-full rounded-full bg-slate-500 opacity-70"
              style={{ width: `${report.overallConfidence}%` }}
            />
          </div>
        </div>
      </div>

      {/* 2×3 grid of dimension cards */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {report.items.map((item) => (
          <DimensionCard key={item.dimension} item={item} />
        ))}
      </div>

      <p className="text-[10px] text-[var(--chitta-muted)] leading-relaxed">
        Quality reflects public data availability at screening stage. All sites require on-site
        measurement before any investment commitment.
      </p>
    </div>
  );
}
