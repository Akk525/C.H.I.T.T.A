"use client";

import { useState } from "react";
import type {
  DevelopmentOutlook,
  DevelopmentOutlookVerdict,
  FatalFlaw,
  FitnessResult,
  RiskItem,
  RiskLevel,
} from "@/lib/types";

type Props = {
  outlook: DevelopmentOutlook;
};

// ── Color helpers ─────────────────────────────────────────────────────────────

function outlookColors(verdict: DevelopmentOutlookVerdict) {
  switch (verdict) {
    case "not_recommended":
      return { bg: "bg-rose-50", border: "border-rose-200", text: "text-rose-800", badge: "bg-rose-700 text-white" };
    case "high_risk":
      return { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-800", badge: "bg-amber-600 text-white" };
    case "fragile":
      return { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-800", badge: "bg-blue-600 text-white" };
    case "promising":
      return { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-800", badge: "bg-emerald-700 text-white" };
  }
}

function levelColors(level: RiskLevel) {
  switch (level) {
    case "high":    return "bg-rose-100 text-rose-800";
    case "medium":  return "bg-amber-100 text-amber-800";
    case "low":     return "bg-emerald-100 text-emerald-800";
    case "unknown": return "bg-slate-100 text-slate-700";
  }
}

function kcLabel(kc: string) {
  switch (kc) {
    case "known_known":   return "Known";
    case "known_unknown": return "Known ✗";
    case "unknown_known": return "Proxy";
    case "unknown_unknown": return "Unknown";
    default: return kc;
  }
}

function fitBandColors(band: string) {
  switch (band) {
    case "low":       return "text-emerald-700";
    case "medium":    return "text-blue-700";
    case "high":      return "text-amber-700";
    case "very_high": return "text-rose-700";
    default:          return "text-slate-700";
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function OutlookBanner({ outlook }: { outlook: DevelopmentOutlook }) {
  const colors = outlookColors(outlook.developmentOutlook);
  const label = outlook.developmentOutlook.replace(/_/g, " ").toUpperCase();
  return (
    <div className={`rounded-lg border p-4 ${colors.bg} ${colors.border}`}>
      <div className="mb-2 flex items-center gap-2">
        <span className={`rounded-md px-2 py-0.5 text-xs font-bold tracking-wider ${colors.badge}`}>
          {label}
        </span>
        <span className="text-xs font-semibold text-slate-500">Development Outlook</span>
      </div>
      <p className={`text-sm leading-relaxed ${colors.text}`}>{outlook.narrativeSummary}</p>
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="chitta-panel rounded-lg p-3 text-center">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--chitta-muted)]">{label}</p>
      <p className="chitta-mono text-xl font-bold text-[var(--chitta-ink)]">{value}</p>
      {sub && <p className="text-[10px] text-[var(--chitta-muted)]">{sub}</p>}
    </div>
  );
}

function FatalFlawsList({ flaws }: { flaws: FatalFlaw[] }) {
  if (flaws.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--chitta-ink)]">
        Potential Fatal Flaws
      </h3>
      <div className="space-y-2">
        {flaws.map((flaw) => (
          <div
            key={flaw.id}
            className={`rounded-lg border p-3 ${
              flaw.severity === "critical"
                ? "border-rose-200 bg-rose-50"
                : "border-amber-200 bg-amber-50"
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="mt-0.5 shrink-0 text-base">
                {flaw.severity === "critical" ? "⛔" : "⚠️"}
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                      flaw.severity === "critical"
                        ? "bg-rose-700 text-white"
                        : "bg-amber-600 text-white"
                    }`}
                  >
                    {flaw.severity}
                  </span>
                  <span className="text-slate-700">{flaw.category}</span>
                </div>
                <p className="mt-1 text-xs text-slate-700">{flaw.description}</p>
                <p className="mt-1 text-[10px] text-slate-500">
                  <span className="font-medium">Next step: </span>
                  {flaw.nextStep}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RiskRegisterTable({ items }: { items: RiskItem[] }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--chitta-ink)]">
        Risk Register
      </h3>
      <div className="overflow-x-auto rounded-lg border border-[var(--chitta-border)]">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[var(--chitta-border)] bg-[var(--chitta-surface)]">
              <th className="px-3 py-2 text-left font-semibold text-[var(--chitta-muted)]">Category</th>
              <th className="px-3 py-2 text-left font-semibold text-[var(--chitta-muted)]">Level</th>
              <th className="px-3 py-2 text-left font-semibold text-[var(--chitta-muted)] hidden sm:table-cell">Knowledge</th>
              <th className="px-3 py-2 text-left font-semibold text-[var(--chitta-muted)]">Summary</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr
                key={item.category}
                className={`border-b border-[var(--chitta-border)] last:border-0 ${
                  i % 2 === 0 ? "bg-[var(--chitta-bg)]" : "bg-[var(--chitta-surface)]"
                }`}
              >
                <td className="px-3 py-2 font-medium text-[var(--chitta-ink)]">{item.category}</td>
                <td className="px-3 py-2">
                  <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${levelColors(item.level)}`}>
                    {item.level}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-500 hidden sm:table-cell">{kcLabel(item.knowledgeClass)}</td>
                <td className="px-3 py-2 text-slate-600">{item.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FitnessTests({ fitness }: { fitness: FitnessResult }) {
  const [expanded, setExpanded] = useState(false);
  const bandClass = fitBandColors(fitness.riskBand);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--chitta-ink)]">
          Project Fitness Tests
        </h3>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-[10px] font-medium text-[var(--chitta-accent)] hover:underline"
        >
          {expanded ? "Hide tests" : "Show all 10 tests"}
        </button>
      </div>
      <div className="mb-2 rounded-lg border border-[var(--chitta-border)] bg-[var(--chitta-surface)] px-3 py-2">
        <p className="text-xs">
          <span className="font-semibold text-[var(--chitta-ink)]">
            {fitness.testsPassed}/{fitness.totalTests} tests passed
          </span>
          {" — "}
          <span className={`font-semibold ${bandClass}`}>
            {fitness.riskBand.replace("_", " ").toUpperCase()} risk band
          </span>
        </p>
        <p className="mt-1 text-[11px] text-slate-500">{fitness.interpretation}</p>
        {fitness.mostVulnerableAssumptions.length > 0 && (
          <p className="mt-1 text-[11px] text-slate-500">
            <span className="font-medium">Most vulnerable: </span>
            {fitness.mostVulnerableAssumptions.join("; ")}
          </p>
        )}
      </div>
      {expanded && (
        <div className="space-y-1">
          {fitness.tests.map((test) => (
            <div
              key={test.testName}
              className={`flex items-start gap-2 rounded px-3 py-2 text-xs ${
                test.passed
                  ? "bg-emerald-50 text-emerald-900"
                  : "bg-rose-50 text-rose-900"
              }`}
            >
              <span className="shrink-0 font-bold">{test.passed ? "✓" : "✗"}</span>
              <div className="min-w-0">
                <span className="font-medium">{test.testName}</span>
                {" — "}
                <span className="text-slate-600">{test.impactSummary}</span>
                {!test.passed && test.failureReason && (
                  <p className="mt-0.5 text-[10px] text-rose-700">{test.failureReason}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NextPriorities({ priorities }: { priorities: string[] }) {
  if (priorities.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-[var(--chitta-ink)]">
        Next Investigation Priorities
      </h3>
      <ol className="space-y-1">
        {priorities.map((p, i) => (
          <li key={i} className="flex gap-2 text-xs text-slate-700">
            <span className="chitta-mono shrink-0 font-bold text-[var(--chitta-accent)]">{i + 1}.</span>
            <span>{p}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function DevelopmentRiskPanel({ outlook }: Props) {
  const criticalCount = outlook.riskRegister.criticalFatalFlawCount;
  const warningCount = outlook.fatalFlaws.filter((f) => f.severity === "warning").length;
  const unknownCount = outlook.riskRegister.categories.filter((c) => c.level === "unknown").length;
  const fitness = outlook.fitnessTest;

  return (
    <div className="space-y-5">
      <OutlookBanner outlook={outlook} />

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatCard
          label="Critical Flaws"
          value={criticalCount}
          sub={criticalCount === 0 ? "None identified" : "Require resolution"}
        />
        <StatCard
          label="Warnings"
          value={warningCount}
          sub={warningCount === 0 ? "None identified" : "Require investigation"}
        />
        <StatCard
          label="Known Unknowns"
          value={unknownCount}
          sub="Risk categories"
        />
        <StatCard
          label="Fitness Score"
          value={`${fitness.testsPassed}/10`}
          sub={fitness.riskBand.replace("_", " ") + " risk"}
        />
      </div>

      {outlook.fatalFlaws.length > 0 && (
        <FatalFlawsList flaws={outlook.fatalFlaws} />
      )}

      <RiskRegisterTable items={outlook.riskRegister.categories} />
      <FitnessTests fitness={fitness} />
      <NextPriorities priorities={outlook.nextInvestigationPriorities} />
    </div>
  );
}
