"use client";

import { useState } from "react";
import { computeEconomics, DEFAULT_ASSUMPTIONS, type LocalEconomicInputs } from "@/lib/economics";
import type { EconomicMetrics } from "@/lib/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`;
  return `$${v.toFixed(0)}`;
}

function scoreColour(v: number): string {
  if (v >= 70) return "text-emerald-700";
  if (v >= 50) return "text-blue-700";
  if (v >= 35) return "text-amber-700";
  return "text-rose-700";
}

function MetricCard({
  label,
  value,
  sub,
  colour,
}: {
  label: string;
  value: string;
  sub?: string;
  colour?: string;
}) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2.5">
      <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-base font-bold ${colour ?? "text-slate-900"}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-400 mt-0.5">{sub}</div>}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function EconomicsPanel({
  metrics,
  windSpeedAtHub,
  terrainScore,
  infraScore,
}: {
  metrics: EconomicMetrics;
  windSpeedAtHub: number | null;
  terrainScore?: number | null;
  infraScore?: number | null;
}) {
  const [open, setOpen] = useState(false);
  const [showLimitations, setShowLimitations] = useState(false);

  // Local slider state for client-side recompute
  const [inputs, setInputs] = useState<LocalEconomicInputs>({
    turbineRatingMw: metrics.assumptions.turbineRatingMw,
    turbineCount: metrics.assumptions.turbineCount,
    electricityPriceUsdPerMwh: metrics.assumptions.electricityPriceUsdPerMwh,
    capexUsdPerMw: metrics.assumptions.capexUsdPerMw,
    opexPctOfCapex: metrics.assumptions.opexPctOfCapex,
    projectLifeYears: metrics.assumptions.projectLifeYears,
    discountRate: metrics.assumptions.discountRate,
  });

  // Live-computed metrics (or server metrics when inputs are at defaults)
  const live = computeEconomics(windSpeedAtHub, terrainScore ?? null, infraScore ?? null, inputs);
  const eco = live;

  const scoreClr = scoreColour(eco.economicScore);

  return (
    <div className="chitta-card rounded-xl bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div>
          <div className="text-sm font-semibold text-slate-900">Economic Feasibility</div>
          <div className="mt-0.5 text-xs text-slate-500">
            Preliminary screening estimate — not investment-grade
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-lg font-bold ${scoreClr}`}>
            {eco.economicScore.toFixed(0)}
          </span>
          <span className="text-slate-400">{open ? "▾" : "▸"}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 py-4 space-y-4">
          {/* Metric cards */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <MetricCard
              label="Capacity factor"
              value={`${(eco.capacityFactor * 100).toFixed(1)}%`}
              sub="At hub height"
              colour={eco.capacityFactor >= 0.30 ? "text-emerald-700" : eco.capacityFactor >= 0.20 ? "text-amber-700" : "text-rose-700"}
            />
            <MetricCard
              label="Annual energy"
              value={`${(eco.annualEnergyMwh / 1000).toFixed(1)} GWh/yr`}
              sub={`${inputs.turbineCount} × ${inputs.turbineRatingMw}MW`}
            />
            <MetricCard
              label="CAPEX estimate"
              value={fmtUsd(eco.capexUsd)}
              sub="±30–50% accuracy"
            />
            <MetricCard
              label="OPEX / year"
              value={fmtUsd(eco.opexUsdPerYear)}
              sub={`${(inputs.opexPctOfCapex * 100).toFixed(0)}% of CAPEX`}
            />
            <MetricCard
              label="Revenue / year"
              value={fmtUsd(eco.annualRevenueUsd)}
              sub={`@ $${inputs.electricityPriceUsdPerMwh}/MWh`}
              colour="text-emerald-700"
            />
            <MetricCard
              label="LCOE"
              value={`$${eco.lcoeUsdPerMwh.toFixed(0)}/MWh`}
              sub={`${(inputs.discountRate * 100).toFixed(0)}% discount`}
              colour={eco.lcoeUsdPerMwh < 60 ? "text-emerald-700" : eco.lcoeUsdPerMwh < 75 ? "text-amber-700" : "text-rose-700"}
            />
          </div>

          {/* Payback */}
          <div className={`rounded-xl px-4 py-3 text-sm font-medium ${
            eco.paybackYears !== null && eco.paybackYears <= 15
              ? "bg-emerald-50 text-emerald-800"
              : "bg-amber-50 text-amber-800"
          }`}>
            {eco.paybackYears !== null
              ? `Simple payback: ${eco.paybackYears.toFixed(1)} years`
              : "Payback period: N/A — revenue does not exceed OPEX at current assumptions"}
          </div>

          {/* Sliders */}
          <div className="space-y-3 border-t border-slate-100 pt-3">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
              Adjust assumptions (live recompute)
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <label className="text-xs text-slate-600 block mb-1">
                  Turbines: <span className="font-semibold">{inputs.turbineCount}</span>
                </label>
                <input
                  type="range" min={3} max={30} step={1}
                  value={inputs.turbineCount}
                  onChange={(e) => setInputs((p) => ({ ...p, turbineCount: parseInt(e.target.value) }))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="text-xs text-slate-600 block mb-1">
                  Rating: <span className="font-semibold">{inputs.turbineRatingMw}MW</span>
                </label>
                <input
                  type="range" min={1} max={6} step={0.5}
                  value={inputs.turbineRatingMw}
                  onChange={(e) => setInputs((p) => ({ ...p, turbineRatingMw: parseFloat(e.target.value) }))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="text-xs text-slate-600 block mb-1">
                  Price: <span className="font-semibold">${inputs.electricityPriceUsdPerMwh}/MWh</span>
                </label>
                <input
                  type="range" min={30} max={120} step={5}
                  value={inputs.electricityPriceUsdPerMwh}
                  onChange={(e) => setInputs((p) => ({ ...p, electricityPriceUsdPerMwh: parseInt(e.target.value) }))}
                  className="w-full"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={() => setInputs({ ...DEFAULT_ASSUMPTIONS })}
              className="text-xs text-emerald-700 hover:underline"
            >
              Reset to defaults
            </button>
          </div>

          {/* Limitations */}
          <div className="border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setShowLimitations((v) => !v)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              {showLimitations ? "Hide" : "Show"} methodology & limitations
            </button>
            {showLimitations && (
              <ul className="mt-2 space-y-1">
                {metrics.limitations.map((l, i) => (
                  <li key={i} className="text-[11px] italic text-slate-400 flex gap-1.5">
                    <span className="shrink-0">·</span>
                    <span>{l}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
