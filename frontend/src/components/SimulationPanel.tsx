"use client";

import { useState } from "react";
import { runSimulation } from "@/lib/api";
import {
  DEFAULT_SIMULATION_CONFIG,
  type CandidateRankingChange,
  type ProspectingCandidate,
  type SimulatedCandidate,
  type SimulationConfig,
  type SimulationResponse,
} from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Props {
  candidates: ProspectingCandidate[];
  onClose: () => void;
  onResult?: (result: SimulationResponse) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const WEIGHT_KEYS: Array<{
  key: keyof SimulationConfig;
  label: string;
  normKey: string;
}> = [
  { key: "windWeight",            label: "Wind",            normKey: "wind"           },
  { key: "terrainWeight",         label: "Terrain",         normKey: "terrain"        },
  { key: "infrastructureWeight",  label: "Infrastructure",  normKey: "infrastructure" },
  { key: "environmentalWeight",   label: "Environmental",   normKey: "environmental"  },
  { key: "populationWeight",      label: "Population",      normKey: "population"     },
  { key: "confidenceWeight",      label: "Confidence",      normKey: "confidence"     },
  { key: "economicWeight",        label: "Economic",        normKey: "economic"       },
];

function normalizeWeights(config: SimulationConfig): Record<string, number> {
  const raw: Record<string, number> = {
    wind:           config.windWeight,
    terrain:        config.terrainWeight,
    infrastructure: config.infrastructureWeight,
    environmental:  config.environmentalWeight,
    population:     config.populationWeight,
    confidence:     config.confidenceWeight,
    economic:       config.economicWeight,
  };
  const total = Object.values(raw).reduce((s, v) => s + Math.max(0, v), 0);
  if (total === 0) return Object.fromEntries(Object.keys(raw).map((k) => [k, 0]));
  return Object.fromEntries(
    Object.entries(raw).map(([k, v]) => [k, (Math.max(0, v) / total) * 100]),
  );
}

function scoreColour(v: number | null): string {
  if (v === null) return "text-slate-400";
  if (v >= 70) return "text-emerald-700";
  if (v >= 55) return "text-blue-700";
  if (v >= 40) return "text-amber-700";
  return "text-rose-700";
}

function DecisionBadge({ d }: { d: string | null }) {
  if (!d) return null;
  const cls: Record<string, string> = {
    promising: "bg-emerald-100 text-emerald-800",
    mixed:     "bg-blue-100 text-blue-800",
    caution:   "bg-amber-100 text-amber-800",
    poor:      "bg-rose-100 text-rose-800",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${cls[d] ?? "bg-slate-100 text-slate-600"}`}
    >
      {d}
    </span>
  );
}

function RankChange({ rc }: { rc: CandidateRankingChange }) {
  if (rc.direction === "up")
    return <span className="font-semibold text-emerald-600">↑ +{rc.rankChange}</span>;
  if (rc.direction === "down")
    return <span className="font-semibold text-rose-600">↓ {rc.rankChange}</span>;
  return <span className="text-slate-400">=</span>;
}

function DeltaDisplay({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-slate-400">–</span>;
  const sign = delta > 0 ? "+" : "";
  const cls =
    delta > 0 ? "text-emerald-600" : delta < 0 ? "text-rose-600" : "text-slate-400";
  return <span className={cls}>{sign}{delta.toFixed(1)}</span>;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-medium text-slate-800">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-blue-600"
      />
    </div>
  );
}

function SummaryCandidateCard({
  label,
  icon,
  cand,
}: {
  label: string;
  icon: string;
  cand: SimulatedCandidate;
}) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-2.5">
      <div className="mb-1 text-[10px] font-semibold text-slate-500">
        {icon} {label.toUpperCase()}
      </div>
      <div className={`text-sm font-bold ${scoreColour(cand.newTotalSuitability)}`}>
        {cand.newTotalSuitability?.toFixed(0) ?? "–"}
      </div>
      <div className="text-[10px] text-slate-400">
        {cand.latitude.toFixed(2)}, {cand.longitude.toFixed(2)}
      </div>
      <div className="mt-1">
        <DecisionBadge d={cand.newDecision} />
      </div>
      {cand.suitabilityDelta !== null && (
        <div className="mt-0.5 text-[10px]">
          <DeltaDisplay delta={cand.suitabilityDelta} /> pts
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function SimulationPanel({ candidates, onClose, onResult }: Props) {
  const [config, setConfig] = useState<SimulationConfig>({ ...DEFAULT_SIMULATION_CONFIG });
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openSections, setOpenSections] = useState({
    economic: true,
    weights: true,
    policy: false,
  });

  const normWeights = normalizeWeights(config);
  const totalRawWeight = WEIGHT_KEYS.reduce(
    (s, { key }) => s + Math.max(0, config[key] as number),
    0,
  );

  function update<K extends keyof SimulationConfig>(key: K, value: SimulationConfig[K]) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  function toggleSection(s: keyof typeof openSections) {
    setOpenSections((prev) => ({ ...prev, [s]: !prev[s] }));
  }

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const res = await runSimulation({ candidates, config });
      setResult(res);
      onResult?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  // Build human-readable diff vs defaults for the summary callout
  const D = DEFAULT_SIMULATION_CONFIG;
  const configDiffs: string[] = [];
  if (config.electricityPriceUsdPerMwh !== D.electricityPriceUsdPerMwh)
    configDiffs.push(
      `Electricity price: $${D.electricityPriceUsdPerMwh} → $${config.electricityPriceUsdPerMwh}/MWh`,
    );
  if (config.capexUsdPerMw !== D.capexUsdPerMw)
    configDiffs.push(
      `CAPEX: $${(D.capexUsdPerMw / 1e6).toFixed(2)}M → $${(config.capexUsdPerMw / 1e6).toFixed(2)}M/MW`,
    );
  if (
    config.turbineCount !== D.turbineCount ||
    config.turbineRatingMw !== D.turbineRatingMw
  )
    configDiffs.push(
      `Farm size: ${D.turbineCount}×${D.turbineRatingMw}MW → ${config.turbineCount}×${config.turbineRatingMw}MW`,
    );
  if (config.projectLifeYears !== D.projectLifeYears)
    configDiffs.push(`Project life: ${D.projectLifeYears}yr → ${config.projectLifeYears}yr`);
  if (config.opexPercentOfCapex !== D.opexPercentOfCapex)
    configDiffs.push(
      `OPEX: ${(D.opexPercentOfCapex * 100).toFixed(1)}% → ${(config.opexPercentOfCapex * 100).toFixed(1)}% of CAPEX`,
    );
  if (config.environmentalStrictness !== D.environmentalStrictness)
    configDiffs.push(
      `Env strictness: ${D.environmentalStrictness} → ${config.environmentalStrictness}`,
    );
  if (config.infrastructurePreference !== D.infrastructurePreference)
    configDiffs.push(
      `Infra preference: ${D.infrastructurePreference} → ${config.infrastructurePreference}`,
    );

  return (
    <div className="chitta-card overflow-hidden rounded-xl border border-blue-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-[0.12em] text-blue-700">
              SCENARIO SIMULATION
            </span>
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">
              sim-1.0
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Recompute rankings with different assumptions — no data providers called.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-lg leading-none text-slate-400 hover:text-slate-600"
          aria-label="Close simulation panel"
        >
          ×
        </button>
      </div>

      <div className="grid grid-cols-1 divide-y divide-slate-100 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
        {/* ── Left: Config ──────────────────────────────────────────────────── */}
        <div className="space-y-4 p-5">
          {/* Economic Assumptions */}
          <section>
            <button
              type="button"
              onClick={() => toggleSection("economic")}
              className="mb-3 flex w-full items-center justify-between text-xs font-semibold tracking-[0.10em] text-slate-500"
            >
              <span>ECONOMIC ASSUMPTIONS</span>
              <span className="text-slate-400">{openSections.economic ? "▲" : "▼"}</span>
            </button>
            {openSections.economic && (
              <div className="space-y-3">
                <SliderRow
                  label="Turbine count"
                  value={config.turbineCount}
                  min={3} max={30} step={1}
                  format={(v) => `${v}`}
                  onChange={(v) => update("turbineCount", Math.round(v))}
                />
                <SliderRow
                  label="Turbine rating (MW)"
                  value={config.turbineRatingMw}
                  min={1} max={8} step={0.5}
                  format={(v) => `${v} MW`}
                  onChange={(v) => update("turbineRatingMw", v)}
                />
                <SliderRow
                  label="Electricity price ($/MWh)"
                  value={config.electricityPriceUsdPerMwh}
                  min={20} max={150} step={5}
                  format={(v) => `$${v}`}
                  onChange={(v) => update("electricityPriceUsdPerMwh", v)}
                />
                <SliderRow
                  label="CAPEX ($/MW)"
                  value={config.capexUsdPerMw}
                  min={800_000} max={2_500_000} step={50_000}
                  format={(v) => `$${(v / 1e6).toFixed(2)}M`}
                  onChange={(v) => update("capexUsdPerMw", v)}
                />
                <SliderRow
                  label="OPEX (% of CAPEX / yr)"
                  value={config.opexPercentOfCapex * 100}
                  min={1} max={5} step={0.5}
                  format={(v) => `${v.toFixed(1)}%`}
                  onChange={(v) => update("opexPercentOfCapex", v / 100)}
                />
                <SliderRow
                  label="Project life (years)"
                  value={config.projectLifeYears}
                  min={10} max={30} step={5}
                  format={(v) => `${v}yr`}
                  onChange={(v) => update("projectLifeYears", Math.round(v))}
                />
              </div>
            )}
          </section>

          {/* Scoring Weights */}
          <section>
            <button
              type="button"
              onClick={() => toggleSection("weights")}
              className="mb-3 flex w-full items-center justify-between text-xs font-semibold tracking-[0.10em] text-slate-500"
            >
              <span>SCORING WEIGHTS</span>
              <span className="text-slate-400">{openSections.weights ? "▲" : "▼"}</span>
            </button>
            {openSections.weights && (
              <div className="space-y-3">
                {totalRawWeight === 0 && (
                  <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
                    All weights are zero — set at least one positive weight.
                  </div>
                )}
                {WEIGHT_KEYS.map(({ key, label, normKey }) => {
                  const pct = normWeights[normKey] ?? 0;
                  return (
                    <div key={key}>
                      <div className="mb-1 flex justify-between text-xs text-slate-600">
                        <span>{label}</span>
                        <span className="text-slate-400">
                          {(config[key] as number).toFixed(0)} →{" "}
                          <span className="font-medium text-slate-700">
                            {pct.toFixed(1)}%
                          </span>
                        </span>
                      </div>
                      <input
                        type="range"
                        min={0} max={50} step={1}
                        value={config[key] as number}
                        onChange={(e) => update(key, parseFloat(e.target.value))}
                        className="w-full accent-blue-600"
                      />
                    </div>
                  );
                })}
                <p className="text-[10px] text-slate-400">
                  Economic is a full weighted dimension — not the v2.1.0 ±8pt nudge.
                </p>
              </div>
            )}
          </section>

          {/* Policy Settings */}
          <section>
            <button
              type="button"
              onClick={() => toggleSection("policy")}
              className="mb-3 flex w-full items-center justify-between text-xs font-semibold tracking-[0.10em] text-slate-500"
            >
              <span>POLICY SETTINGS</span>
              <span className="text-slate-400">{openSections.policy ? "▲" : "▼"}</span>
            </button>
            {openSections.policy && (
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs text-slate-600">
                    Environmental strictness
                  </label>
                  <select
                    value={config.environmentalStrictness}
                    onChange={(e) =>
                      update(
                        "environmentalStrictness",
                        e.target.value as "low" | "medium" | "high",
                      )
                    }
                    className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-300"
                  >
                    <option value="low">Low — relaxed environmental constraints</option>
                    <option value="medium">Medium — standard (default)</option>
                    <option value="high">High — strict environmental requirements</option>
                  </select>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {config.environmentalStrictness === "low" &&
                      "Environmental score ×1.25 — less concern for land cover / protected areas"}
                    {config.environmentalStrictness === "medium" &&
                      "No modification to environmental scores"}
                    {config.environmentalStrictness === "high" &&
                      "Environmental score ×0.65 — stricter constraints penalise marginal sites"}
                  </p>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-600">
                    Infrastructure preference
                  </label>
                  <select
                    value={config.infrastructurePreference}
                    onChange={(e) =>
                      update(
                        "infrastructurePreference",
                        e.target.value as "remote" | "balanced" | "grid-connected",
                      )
                    }
                    className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-300"
                  >
                    <option value="remote">Remote — penalise grid proximity less</option>
                    <option value="balanced">Balanced — standard (default)</option>
                    <option value="grid-connected">
                      Grid-connected — reward grid proximity
                    </option>
                  </select>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {config.infrastructurePreference === "remote" &&
                      "Infrastructure score ×0.75 — remote sites tolerated"}
                    {config.infrastructurePreference === "balanced" &&
                      "No modification to infrastructure scores"}
                    {config.infrastructurePreference === "grid-connected" &&
                      "Infrastructure score ×1.30 — well-connected sites favoured"}
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => {
                setConfig({ ...DEFAULT_SIMULATION_CONFIG });
                setResult(null);
              }}
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600 transition-colors hover:bg-slate-50"
            >
              Reset to defaults
            </button>
            <button
              type="button"
              onClick={handleRun}
              disabled={loading || totalRawWeight === 0}
              className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Computing…" : "Run Simulation"}
            </button>
          </div>

          {error && (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800">
              {error}
            </div>
          )}
        </div>

        {/* ── Right: Results ────────────────────────────────────────────────── */}
        <div className="p-5">
          {!result && !loading && (
            <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 text-center">
              <div>
                <div className="text-sm text-slate-400">No simulation run yet</div>
                <div className="mt-1 text-xs text-slate-400">
                  Adjust parameters and click Run Simulation.
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex h-full min-h-[200px] items-center justify-center text-sm text-blue-600">
              Computing scenario…
            </div>
          )}

          {result && !loading && (
            <div className="space-y-4">
              {/* Config diff callout */}
              {configDiffs.length > 0 && (
                <div className="rounded-lg bg-blue-50 px-3 py-2">
                  <div className="mb-1 text-[10px] font-semibold text-blue-700">
                    SCENARIO CHANGES
                  </div>
                  {configDiffs.map((d, i) => (
                    <div key={i} className="text-[11px] text-blue-700">
                      {d}
                    </div>
                  ))}
                  <div className="mt-1 text-[10px] text-blue-500">
                    Formula: sim-1.0 (economic as full weight, not nudge)
                  </div>
                </div>
              )}

              {/* Summary cards */}
              <div className="grid grid-cols-2 gap-2">
                {result.strongestCandidate && (
                  <SummaryCandidateCard
                    label="Strongest"
                    icon="↑"
                    cand={result.strongestCandidate}
                  />
                )}
                {result.weakestCandidate && (
                  <SummaryCandidateCard
                    label="Weakest"
                    icon="↓"
                    cand={result.weakestCandidate}
                  />
                )}
                {result.mostImprovedCandidate && (
                  <SummaryCandidateCard
                    label="Most Improved"
                    icon="+"
                    cand={result.mostImprovedCandidate}
                  />
                )}
                {result.mostSensitiveCandidate && (
                  <SummaryCandidateCard
                    label="Most Sensitive"
                    icon="~"
                    cand={result.mostSensitiveCandidate}
                  />
                )}
              </div>

              {/* Ranking table */}
              {result.rankingChanges.length > 0 && (
                <div>
                  <div className="mb-2 text-[10px] font-semibold tracking-[0.12em] text-slate-500">
                    RECOMPUTED RANKINGS
                  </div>
                  <div className="overflow-hidden rounded-xl border border-slate-100">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-100 bg-slate-50 text-left text-[11px] text-slate-500">
                          <th className="px-3 py-2 font-medium">New</th>
                          <th className="px-3 py-2 font-medium">Change</th>
                          <th className="px-3 py-2 font-medium">Score</th>
                          <th className="px-3 py-2 font-medium">Δ</th>
                          <th className="px-3 py-2 font-medium">Decision</th>
                          <th className="px-3 py-2 font-medium">Coordinates</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.rankingChanges.map((rc) => {
                          const sim = result.recomputedCandidates.find(
                            (c) => c.id === rc.id,
                          );
                          return (
                            <tr
                              key={rc.id}
                              className="border-b border-slate-50 transition-colors hover:bg-slate-50"
                            >
                              <td className="px-3 py-2 text-slate-600">
                                #{rc.newRank}
                              </td>
                              <td className="px-3 py-2">
                                <RankChange rc={rc} />
                              </td>
                              <td
                                className={`px-3 py-2 font-semibold ${scoreColour(sim?.newTotalSuitability ?? null)}`}
                              >
                                {sim?.newTotalSuitability?.toFixed(0) ?? "–"}
                              </td>
                              <td className="px-3 py-2">
                                <DeltaDisplay delta={sim?.suitabilityDelta ?? null} />
                              </td>
                              <td className="px-3 py-2">
                                <DecisionBadge d={sim?.newDecision ?? null} />
                              </td>
                              <td className="px-3 py-2 text-slate-400">
                                {rc.latitude.toFixed(2)}, {rc.longitude.toFixed(2)}
                                <span className="ml-1 text-slate-300">
                                  (was #{rc.originalRank})
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Methodology */}
              <details className="rounded-lg border border-slate-100 bg-slate-50">
                <summary className="cursor-pointer px-3 py-2 text-[10px] font-semibold text-slate-500">
                  METHODOLOGY & AUDIT
                </summary>
                <div className="space-y-0.5 px-3 pb-3 pt-1">
                  {Object.entries(result.methodology).map(([k, v]) => (
                    <div key={k} className="text-[10px] text-slate-500">
                      <span className="font-medium text-slate-600">{k}:</span> {v}
                    </div>
                  ))}
                  <div className="mt-2 border-t border-slate-100 pt-2">
                    {result.auditTrail.map((line, i) => (
                      <div key={i} className="text-[10px] text-slate-400">
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
