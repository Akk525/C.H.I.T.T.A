"use client";

import { useState } from "react";
import type { InformationValueItem, InformationValueReport } from "@/lib/types";

type Props = {
  report: InformationValueReport;
};

function ivBarColor(iv: number): string {
  if (iv >= 6) return "bg-rose-500";
  if (iv >= 4) return "bg-amber-400";
  return "bg-slate-400";
}

function ivBadgeColor(iv: number): string {
  if (iv >= 6) return "bg-rose-100 text-rose-800";
  if (iv >= 4) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

function IVRow({ item, rank }: { item: InformationValueItem; rank: number }) {
  const [expanded, setExpanded] = useState(false);
  const barWidth = `${(item.informationValue / 10) * 100}%`;

  return (
    <div className="border-b border-[var(--chitta-border)] last:border-0">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-3 py-2.5 text-left hover:bg-[var(--chitta-surface)] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="chitta-mono shrink-0 w-5 text-center text-[10px] font-bold text-[var(--chitta-muted)]">
            {rank}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold text-[var(--chitta-ink)]">{item.category}</span>
              <span
                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold chitta-mono ${ivBadgeColor(item.informationValue)}`}
              >
                {item.informationValue.toFixed(1)}
              </span>
            </div>
            {/* IV bar */}
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${ivBarColor(item.informationValue)}`}
                style={{ width: barWidth }}
              />
            </div>
          </div>
          <span className="shrink-0 text-[10px] text-[var(--chitta-muted)] ml-1">
            {expanded ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 text-xs space-y-2 bg-[var(--chitta-surface)]">
          <p className="text-slate-600 leading-relaxed">{item.informationGap}</p>
          <div className="flex gap-4">
            <span className="text-slate-500">
              <span className="font-medium">Impact:</span> {item.impact.toFixed(0)}/10
            </span>
            <span className="text-slate-500">
              <span className="font-medium">Uncertainty:</span> {item.uncertainty.toFixed(0)}/10
            </span>
          </div>
          <div className="rounded bg-[var(--chitta-bg)] border border-[var(--chitta-border)] px-2.5 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--chitta-muted)] mb-0.5">
              Recommended action
            </p>
            <p className="text-slate-700">{item.recommendedAction}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export function InformationValuePanel({ report }: Props) {
  const top = report.items[0];

  return (
    <div className="space-y-3">
      <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--chitta-ink)]">
        Most Valuable Missing Information
      </h2>

      {/* Top priority callout */}
      {top && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <div className="flex items-start gap-2">
            <span className="text-base shrink-0">🎯</span>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-xs font-bold text-rose-800">Top priority:</span>
                <span
                  className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold chitta-mono ${ivBadgeColor(top.informationValue)}`}
                >
                  IV {top.informationValue.toFixed(1)}/10
                </span>
              </div>
              <p className="text-xs font-semibold text-rose-900">{top.category}</p>
              <p className="mt-0.5 text-[11px] text-rose-800 leading-relaxed">{top.informationGap}</p>
              <p className="mt-1 text-[11px] text-rose-700">
                <span className="font-medium">Action: </span>
                {top.recommendedAction}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Ranked list */}
      <div className="chitta-panel rounded-lg overflow-hidden">
        {report.items.map((item, i) => (
          <IVRow key={item.category} item={item} rank={i + 1} />
        ))}
      </div>

      <p className="text-[10px] text-[var(--chitta-muted)] leading-relaxed">
        IV = Decision Impact × Uncertainty / 10. Higher score means this information would most
        change the go/no-go decision.
      </p>
    </div>
  );
}
