"use client";

import { useState } from "react";
import type { MethodologyMetadata } from "@/lib/types";
import {
  TOTAL_SUITABILITY_FORMULA_PLAIN,
  WIND_SCORE_FORMULA_PLAIN,
} from "@/lib/methodology";

function hasUnavailableData(fallbackStatus: string) {
  const lower = fallbackStatus.toLowerCase();
  return lower.includes("unavailable") || lower.includes("mock");
}

function statusBadge(fallbackStatus: string) {
  const lower = fallbackStatus.toLowerCase();
  if (lower.includes("unavailable")) {
    return {
      label: "Data unavailable",
      className: "rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-800",
    };
  }
  if (lower.includes("mock")) {
    return {
      label: "Mock fallback used",
      className: "rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900",
    };
  }
  return {
    label: "Real data",
    className: "rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900",
  };
}

export function MethodologyAuditPanel({
  analysisId,
  methodology,
  auditTrail,
  heatmapAuditTrail,
}: {
  analysisId: string;
  methodology: MethodologyMetadata;
  auditTrail: string[];
  heatmapAuditTrail?: string[];
}) {
  const [open, setOpen] = useState(false);
  const badge = statusBadge(methodology.fallbackStatus);
  const showWarning = hasUnavailableData(methodology.fallbackStatus);

  return (
    <div className="chitta-card rounded-xl bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div>
          <div className="text-sm font-semibold text-slate-900">
            Methodology &amp; Audit Trail
          </div>
          <div className="mt-0.5 text-xs text-slate-600">
            {analysisId.slice(0, 8)}… · {methodology.generatedAt}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={badge.className}>{badge.label}</span>
          <span className="text-slate-400">{open ? "▾" : "▸"}</span>
        </div>
      </button>

      {open ? (
        <div className="border-t border-slate-100 px-4 py-4 text-sm text-slate-700">
          {showWarning ? (
            <div className="mb-3 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-700">
              {methodology.fallbackStatus}
            </div>
          ) : null}

          <div className="mb-3 grid gap-2 text-xs">
            <div>
              <span className="font-medium text-slate-900">Analysis ID:</span>{" "}
              <code className="rounded bg-slate-50 px-1 py-0.5">{analysisId}</code>
            </div>
            <div>
              <span className="font-medium text-slate-900">Generated:</span>{" "}
              {methodology.generatedAt}
            </div>
          </div>

          <div className="mb-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs">
              Wind: {methodology.windDataSource}
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs">
              Elevation: {methodology.elevationSource}
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs">
              v{methodology.scoringFormulaVersion}
            </span>
          </div>

          <div className="grid gap-3">
            <section>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Formulas (plain English)
              </h4>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5">
                <li>{WIND_SCORE_FORMULA_PLAIN}</li>
                <li>{TOTAL_SUITABILITY_FORMULA_PLAIN}</li>
                <li>{methodology.terrainRoughnessMethod}</li>
                <li>{methodology.confidenceCalculationMethod}</li>
              </ul>
            </section>

            <section>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Data coverage
              </h4>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5">
                <li>Wind date range: {methodology.windDateRange}</li>
                <li>Data availability: {methodology.fallbackStatus}</li>
              </ul>
            </section>

            <section>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Audit trail
              </h4>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5">
                {auditTrail.map((step, i) => (
                  <li key={`audit-${i}`}>{step}</li>
                ))}
              </ol>
              {heatmapAuditTrail?.length ? (
                <>
                  <h4 className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Heatmap audit trail
                  </h4>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5">
                    {heatmapAuditTrail.map((step, i) => (
                      <li key={`heatmap-audit-${i}`}>{step}</li>
                    ))}
                  </ol>
                </>
              ) : null}
            </section>
          </div>
        </div>
      ) : null}
    </div>
  );
}
