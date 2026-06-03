"use client";

import { LoadingProgress } from "@/components/LoadingProgress";
import { useRef, useState } from "react";
import { runLayoutAnalysis } from "@/lib/api";
import type { LayoutAnalysisResponse, TurbinePosition } from "@/lib/types";

type Props = {
  latitude: number;
  longitude: number;
  onLayoutResult: (turbines: TurbinePosition[] | null) => void;
};

function scoreColour(v: number): string {
  if (v >= 75) return "text-emerald-700";
  if (v >= 50) return "text-blue-700";
  if (v >= 30) return "text-amber-700";
  return "text-rose-700";
}

function MetricCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "good" | "warn" | "neutral";
}) {
  const cls = tone === "good" ? "text-emerald-700" : tone === "warn" ? "text-rose-700" : "text-slate-800";
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="text-[10px] font-semibold tracking-[0.1em] text-slate-400">{label}</div>
      <div className={`mt-0.5 text-lg font-bold leading-tight ${cls}`}>{value}</div>
      {sub && <div className="mt-0.5 text-[10px] text-slate-400">{sub}</div>}
    </div>
  );
}

export function LayoutPanel({ latitude, longitude, onLayoutResult }: Props) {
  const [open, setOpen] = useState(false);
  const [turbineCount, setTurbineCount] = useState(10);
  const [rotorDiameterM, setRotorDiameterM] = useState(120);
  const [windDirDeg, setWindDirDeg] = useState<string>("");
  const [result, setResult] = useState<LayoutAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleGenerate() {
    setError(null);
    setLoading(true);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await runLayoutAnalysis(
        {
          latitude,
          longitude,
          turbineCount,
          rotorDiameterM,
          prevailingWindDirectionDeg: windDirDeg ? parseFloat(windDirDeg) : null,
        },
        abortRef.current.signal,
      );
      setResult(res);
      onLayoutResult(res.turbines);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Layout analysis failed");
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setResult(null);
    onLayoutResult(null);
    setError(null);
  }

  const efficiencyLabel = result
    ? result.layoutEfficiencyScore >= 75
      ? "Efficient"
      : result.layoutEfficiencyScore >= 50
        ? "Moderate"
        : result.layoutEfficiencyScore >= 30
          ? "Fair"
          : "Poor"
    : null;

  return (
    <div className="chitta-card rounded-xl bg-white shadow-sm">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <div className="text-xs font-semibold tracking-[0.12em] text-slate-500">LAYOUT INTELLIGENCE</div>
          <div className="text-sm font-medium text-slate-900">Turbine Layout & Wake Loss</div>
          <div className="text-xs text-slate-400">Simplified Jensen/Park screening</div>
        </div>
        <div className="flex items-center gap-2">
          {result && (
            <span className={`text-sm font-bold ${scoreColour(result.layoutEfficiencyScore)}`}>
              {result.layoutEfficiencyScore.toFixed(0)}/100
            </span>
          )}
          <span className="text-slate-400">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3 space-y-4">
          {/* Configuration */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 mb-1">TURBINES</label>
              <input
                type="number"
                min={1}
                max={50}
                value={turbineCount}
                onChange={(e) => setTurbineCount(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-300"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 mb-1">ROTOR Ø (m)</label>
              <input
                type="number"
                min={50}
                max={300}
                value={rotorDiameterM}
                onChange={(e) => setRotorDiameterM(Math.max(50, parseInt(e.target.value) || 120))}
                className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-300"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 mb-1">WIND FROM (°)</label>
              <input
                type="number"
                min={0}
                max={359}
                placeholder="270"
                value={windDirDeg}
                onChange={(e) => setWindDirDeg(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-300"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              className="flex-1 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Generating layout…" : "Generate Layout"}
            </button>
            {result && (
              <button
                type="button"
                onClick={handleClear}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50"
              >
                Clear
              </button>
            )}
          </div>

          {loading && <LoadingProgress variant="layout" compact />}

          {error && (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800">{error}</div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <MetricCard
                  label="EFFICIENCY"
                  value={`${result.layoutEfficiencyScore.toFixed(0)}/100`}
                  sub={efficiencyLabel ?? undefined}
                  tone={
                    result.layoutEfficiencyScore >= 70
                      ? "good"
                      : result.layoutEfficiencyScore < 40
                        ? "warn"
                        : "neutral"
                  }
                />
                <MetricCard
                  label="WAKE LOSS"
                  value={`${result.estimatedWakeLossPercent.toFixed(1)}%`}
                  sub="single direction"
                  tone={
                    result.estimatedWakeLossPercent < 10
                      ? "good"
                      : result.estimatedWakeLossPercent > 20
                        ? "warn"
                        : "neutral"
                  }
                />
                <MetricCard
                  label="SPACING VIOLATIONS"
                  value={String(result.spacingViolations)}
                  sub={result.spacingViolations > 0 ? "< 3D pairs" : "none detected"}
                  tone={result.spacingViolations > 0 ? "warn" : "good"}
                />
                <MetricCard
                  label="TURBINES PLACED"
                  value={String(result.turbines.length)}
                  sub="shown on map"
                />
              </div>

              {/* Assumptions */}
              <div>
                <div className="mb-1.5 text-[10px] font-semibold tracking-[0.1em] text-slate-400">ASSUMPTIONS</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                  {Object.entries(result.assumptions).map(([k, v]) => (
                    <div key={k} className="flex justify-between py-0.5 text-[10px] text-slate-600 border-b border-slate-50">
                      <span className="text-slate-400">{k}</span>
                      <span className="font-medium">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Warnings */}
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-1">
                <div className="text-[10px] font-semibold text-amber-700">NOTICES</div>
                {result.warnings.map((w, i) => (
                  <div key={i} className="text-[10px] text-amber-800">{w}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
