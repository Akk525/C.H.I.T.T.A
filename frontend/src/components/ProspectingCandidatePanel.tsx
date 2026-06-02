"use client";

import type { ProspectingCandidate } from "@/lib/types";

const DECISION_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  promising: { bg: "bg-emerald-100", text: "text-emerald-800", label: "Promising" },
  mixed:     { bg: "bg-blue-100",    text: "text-blue-800",    label: "Mixed" },
  caution:   { bg: "bg-amber-100",   text: "text-amber-800",   label: "Caution" },
  poor:      { bg: "bg-rose-100",    text: "text-rose-800",    label: "Poor" },
};

function ScoreRow({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const colour = value >= 70 ? "text-emerald-700" : value >= 45 ? "text-slate-700" : "text-rose-700";
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-500">{label}</span>
      <span className={`font-semibold ${colour}`}>{value.toFixed(0)}</span>
    </div>
  );
}

function ProviderBadge({ name, status }: { name: string; status: string }) {
  const cls =
    status === "REAL"
      ? "bg-emerald-50 text-emerald-700"
      : status === "UNAVAILABLE"
        ? "bg-slate-100 text-slate-400"
        : "bg-amber-50 text-amber-700";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${cls}`}>
      {name}: {status}
    </span>
  );
}

export function ProspectingCandidatePanel({
  candidate,
  onClose,
}: {
  candidate: ProspectingCandidate;
  onClose: () => void;
}) {
  const cfg = candidate.finalDecision ? DECISION_CONFIG[candidate.finalDecision] : null;

  return (
    <div className="chitta-card rounded-xl bg-white p-4 shadow-sm space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs text-slate-500">
            {candidate.latitude.toFixed(5)}, {candidate.longitude.toFixed(5)}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {candidate.totalSuitability != null && (
              <span className="text-lg font-bold text-slate-900">
                {candidate.totalSuitability.toFixed(0)}<span className="text-sm text-slate-400">/100</span>
              </span>
            )}
            {cfg && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
                {cfg.label}
              </span>
            )}
            {!candidate.isFullyEnriched && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
                Quick screen
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 text-lg leading-none mt-0.5"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {/* Scores grid */}
      <div className="space-y-1.5 rounded-lg bg-slate-50 px-3 py-2">
        <ScoreRow label="Wind" value={candidate.windScore} />
        <ScoreRow label="Terrain" value={candidate.terrainScore} />
        <ScoreRow label="Infrastructure" value={candidate.infrastructureScore} />
        <ScoreRow label="Environmental" value={candidate.environmentalScore} />
        <ScoreRow label="Population" value={candidate.populationScore} />
        <ScoreRow label="Confidence" value={candidate.confidenceScore} />
      </div>

      {/* Strengths */}
      {candidate.topStrengths.length > 0 && (
        <div>
          <div className="text-[11px] font-semibold text-emerald-800 mb-1">Strengths</div>
          <ul className="space-y-1">
            {candidate.topStrengths.map((s, i) => (
              <li key={i} className="text-xs text-slate-700 flex gap-1.5">
                <span className="text-emerald-500 shrink-0">✓</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Risks */}
      {candidate.topRisks.length > 0 && (
        <div>
          <div className="text-[11px] font-semibold text-rose-800 mb-1">Risks</div>
          <ul className="space-y-1">
            {candidate.topRisks.map((r, i) => (
              <li key={i} className="text-xs text-slate-700 flex gap-1.5">
                <span className="text-rose-500 shrink-0">!</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Provider status */}
      <div className="flex flex-wrap gap-1">
        {Object.entries(candidate.providerStatus).map(([name, status]) => (
          <ProviderBadge key={name} name={name.charAt(0).toUpperCase() + name.slice(1)} status={status} />
        ))}
      </div>

      {candidate.error && (
        <div className="rounded bg-rose-50 px-3 py-2 text-xs text-rose-700">
          Error: {candidate.error}
        </div>
      )}

      {/* Economic summary */}
      {candidate.lcoeUsdPerMwh != null && (
        <div className="rounded-lg bg-slate-50 px-3 py-2 space-y-1">
          <div className="text-[11px] font-semibold text-slate-600 mb-1.5">Economic screening</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {candidate.capacityFactor != null && (
              <div className="flex justify-between">
                <span className="text-slate-400">Capacity factor</span>
                <span className="font-medium">{(candidate.capacityFactor * 100).toFixed(0)}%</span>
              </div>
            )}
            {candidate.annualEnergyMwh != null && (
              <div className="flex justify-between">
                <span className="text-slate-400">AEP</span>
                <span className="font-medium">{(candidate.annualEnergyMwh / 1000).toFixed(1)} GWh/yr</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">LCOE</span>
              <span className="font-medium">${candidate.lcoeUsdPerMwh.toFixed(0)}/MWh</span>
            </div>
            {candidate.paybackYears != null && (
              <div className="flex justify-between">
                <span className="text-slate-400">Payback</span>
                <span className="font-medium">{candidate.paybackYears.toFixed(0)} yr</span>
              </div>
            )}
          </div>
          <div className="text-[10px] italic text-slate-400 pt-1">Preliminary estimate only — see full site analysis for detail.</div>
        </div>
      )}

      {!candidate.isFullyEnriched && (
        <div className="text-[11px] text-slate-400 italic">
          This candidate was screened with wind + terrain only. Select a top candidate for full agent analysis.
        </div>
      )}
    </div>
  );
}
