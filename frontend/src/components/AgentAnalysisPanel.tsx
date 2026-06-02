"use client";

import { useState } from "react";
import type { AgentAnalysis, AgentOutput } from "@/lib/types";

// ── Colour maps ───────────────────────────────────────────────────────────────

const DECISION_CONFIG: Record<
  string,
  { bg: string; border: string; text: string; badge: string; label: string }
> = {
  promising: {
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    text: "text-emerald-900",
    badge: "bg-emerald-100 text-emerald-800",
    label: "Promising",
  },
  mixed: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-900",
    badge: "bg-blue-100 text-blue-800",
    label: "Mixed",
  },
  caution: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-900",
    badge: "bg-amber-100 text-amber-800",
    label: "Caution",
  },
  poor: {
    bg: "bg-rose-50",
    border: "border-rose-200",
    text: "text-rose-900",
    badge: "bg-rose-100 text-rose-800",
    label: "Poor",
  },
};

const STATUS_BADGE: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-800",
  partial: "bg-amber-100 text-amber-800",
  fallback: "bg-slate-100 text-slate-600",
};

const AGENT_ICONS: Record<string, string> = {
  Wind: "🌬",
  Terrain: "⛰",
  Infrastructure: "🛣",
  Environmental: "🌿",
  Social: "🏘",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(100, value)));
  const colour =
    pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-400" : "bg-slate-300";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${colour} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-slate-500">{pct}%</span>
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentOutput }) {
  const [open, setOpen] = useState(false);
  const icon = AGENT_ICONS[agent.agentName] ?? "◆";
  const statusCls = STATUS_BADGE[agent.status] ?? STATUS_BADGE.fallback;
  const hasFallback = agent.status === "fallback";

  return (
    <div className="chitta-card rounded-xl bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base">{icon}</span>
            <span className="text-sm font-semibold text-slate-900">{agent.agentName}</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${statusCls}`}>
              {agent.status}
            </span>
          </div>
          <p className={`mt-1 text-xs leading-5 ${hasFallback ? "text-slate-400 italic" : "text-slate-600"}`}>
            {agent.summary}
          </p>
          {!hasFallback && (
            <div className="mt-1.5">
              <ConfidenceBar value={agent.confidence} />
            </div>
          )}
        </div>
        <span className="shrink-0 text-slate-400 mt-0.5">{open ? "▾" : "▸"}</span>
      </button>

      {open && !hasFallback && (
        <div className="border-t border-slate-100 px-4 py-4 space-y-4 text-xs text-slate-700">
          {agent.findings.length > 0 && (
            <section>
              <h5 className="font-semibold text-emerald-800 mb-1.5">Findings</h5>
              <ul className="space-y-1">
                {agent.findings.map((f, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {agent.risks.length > 0 && (
            <section>
              <h5 className="font-semibold text-rose-800 mb-1.5">Risks</h5>
              <ul className="space-y-1">
                {agent.risks.map((r, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-rose-500 mt-0.5 shrink-0">!</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {agent.evidence.length > 0 && (
            <section>
              <h5 className="font-semibold text-slate-700 mb-1.5">Evidence</h5>
              <table className="w-full border-collapse text-[11px]">
                <thead>
                  <tr className="text-left text-slate-500">
                    <th className="py-1 pr-3 font-medium">Metric</th>
                    <th className="py-1 pr-3 font-medium">Value</th>
                    <th className="py-1 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {agent.evidence.map((ev, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="py-1 pr-3 text-slate-600">{ev.label}</td>
                      <td className="py-1 pr-3 font-medium text-slate-900">{ev.value}</td>
                      <td className="py-1 text-slate-400">{ev.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {agent.recommendations.length > 0 && (
            <section>
              <h5 className="font-semibold text-slate-700 mb-1.5">Recommendations</h5>
              <ul className="space-y-1">
                {agent.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-slate-400 mt-0.5 shrink-0">→</span>
                    <span className="text-slate-600">{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}

      {open && hasFallback && (
        <div className="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
          {agent.risks.length > 0 && <p className="italic">{agent.risks[0]}</p>}
          {agent.recommendations.length > 0 && (
            <p className="mt-1.5 text-slate-400">→ {agent.recommendations[0]}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function AgentAnalysisPanel({ agentAnalysis }: { agentAnalysis: AgentAnalysis }) {
  const { coordinator, agents } = agentAnalysis;
  const dec = coordinator.finalDecision;
  const cfg = DECISION_CONFIG[dec] ?? DECISION_CONFIG.mixed;

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold tracking-[0.14em] text-slate-500">
        AGENT ANALYSIS
      </div>

      {/* Coordinator summary */}
      <div className={`chitta-card rounded-xl border ${cfg.border} ${cfg.bg} p-4`}>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="text-sm font-semibold text-slate-900">Coordinator Assessment</div>
          <span className={`rounded-full px-3 py-0.5 text-xs font-semibold ${cfg.badge}`}>
            {cfg.label}
          </span>
        </div>

        <p className="text-xs text-slate-600 mb-3">{coordinator.confidenceSummary}</p>

        {coordinator.contradictionNotes.length > 0 && (
          <div className="mb-3 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
            <div className="text-[11px] font-semibold text-amber-800 mb-1">Contradictions noted</div>
            <ul className="space-y-1">
              {coordinator.contradictionNotes.map((note, i) => (
                <li key={i} className="text-xs text-amber-900 flex gap-1.5">
                  <span className="shrink-0">⚡</span>
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {coordinator.topStrengths.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-emerald-800 mb-1">Top strengths</div>
              <ul className="space-y-1">
                {coordinator.topStrengths.map((s, i) => (
                  <li key={i} className="text-xs text-slate-700 flex gap-1.5">
                    <span className="text-emerald-500 shrink-0 mt-0.5">✓</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {coordinator.topRisks.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-rose-800 mb-1">Top risks</div>
              <ul className="space-y-1">
                {coordinator.topRisks.map((r, i) => (
                  <li key={i} className="text-xs text-slate-700 flex gap-1.5">
                    <span className="text-rose-500 shrink-0 mt-0.5">!</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {coordinator.nextSteps.length > 0 && (
          <div className="mt-3 border-t border-slate-200 pt-3">
            <div className="text-[11px] font-semibold text-slate-700 mb-1">Next steps</div>
            <ol className="space-y-1 list-decimal pl-4">
              {coordinator.nextSteps.map((s, i) => (
                <li key={i} className="text-xs text-slate-600">{s}</li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {/* Agent cards grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {agents.map((agent) => (
          <AgentCard key={agent.agentName} agent={agent} />
        ))}
      </div>
    </div>
  );
}
