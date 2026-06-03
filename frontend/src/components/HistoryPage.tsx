"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchHistoryCompare, fetchHistoryRuns } from "@/lib/api";
import type { HistorySummaryResponse, SavedRunSummary } from "@/lib/types";

// ── Helpers ────────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  site: "Site Analysis",
  prospecting: "Prospecting",
  simulation: "Simulation",
  synthesis: "AI Synthesis",
  layout: "Layout",
};

const TYPE_FILTERS = ["all", "site", "prospecting", "simulation", "synthesis", "layout"] as const;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function decisionBadge(d: string | null) {
  if (!d) return null;
  const cls: Record<string, string> = {
    promising: "bg-emerald-100 text-emerald-800",
    mixed: "bg-blue-100 text-blue-800",
    caution: "bg-amber-100 text-amber-800",
    poor: "bg-rose-100 text-rose-800",
  };
  return (
    <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${cls[d] ?? "bg-slate-100 text-slate-600"}`}>
      {d}
    </span>
  );
}

function scoreColour(v: number | null) {
  if (v == null) return "text-slate-400";
  if (v >= 70) return "text-emerald-700";
  if (v >= 55) return "text-blue-700";
  if (v >= 40) return "text-amber-700";
  return "text-rose-700";
}

// ── Comparison result panel ────────────────────────────────────────────────────

function ComparisonPanel({ summary }: { summary: HistorySummaryResponse }) {
  const score = summary.deltas.score as Record<string, unknown> | undefined;
  const ranking = summary.deltas.ranking as Record<string, unknown> | undefined;
  const delta = score?.delta as number | null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        <span className="rounded-full bg-indigo-100 px-2.5 py-1 text-[10px] font-semibold text-indigo-700">
          LangGraph historical comparison
        </span>
        <span className="text-[10px] text-slate-400">
          {new Date(summary.generatedAt).toLocaleString()}
        </span>
      </div>

      {/* Score delta */}
      {score && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="text-[10px] font-semibold text-slate-400">CURRENT SCORE</div>
            <div className={`text-lg font-bold ${scoreColour(score.currentScore as number | null)}`}>
              {score.currentScore != null ? `${(score.currentScore as number).toFixed(1)}/100` : "—"}
            </div>
            {decisionBadge(score.currentDecision as string | null)}
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="text-[10px] font-semibold text-slate-400">PREVIOUS SCORE</div>
            <div className={`text-lg font-bold ${scoreColour(score.previousScore as number | null)}`}>
              {score.previousScore != null ? `${(score.previousScore as number).toFixed(1)}/100` : "—"}
            </div>
            {decisionBadge(score.previousDecision as string | null)}
          </div>
          <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="text-[10px] font-semibold text-slate-400">DELTA</div>
            <div className={`text-lg font-bold ${
              delta == null ? "text-slate-400" : delta > 0 ? "text-emerald-700" : delta < 0 ? "text-rose-700" : "text-slate-500"
            }`}>
              {delta != null ? `${delta > 0 ? "+" : ""}${delta.toFixed(1)}` : "—"}
            </div>
            {score.decisionChanged ? (
              <div className="text-[10px] text-amber-700">Decision changed</div>
            ) : (
              <div className="text-[10px] text-slate-400">Same decision</div>
            )}
          </div>
        </div>
      )}

      {/* Narrative */}
      <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
        <div className="text-[10px] font-semibold tracking-[0.1em] text-indigo-600 mb-2">HISTORICAL NARRATIVE</div>
        <p className="text-sm text-indigo-900 leading-relaxed">{summary.historicalNarrative}</p>
      </div>

      {/* Ranking deltas (prospecting) */}
      {ranking && (
        <div>
          <div className="text-[10px] font-semibold tracking-[0.1em] text-slate-400 mb-2">CANDIDATE RANKING CHANGES</div>
          <div className="grid grid-cols-2 gap-3 text-xs text-slate-700">
            {(ranking.significantScoreChanges as unknown[])?.length ? (
              <div>
                <div className="font-medium text-slate-900 mb-1">Score changes</div>
                {(ranking.significantScoreChanges as Array<Record<string, unknown>>).map((c, i) => (
                  <div key={i} className="flex justify-between py-0.5 border-b border-slate-50">
                    <span className="text-slate-400 font-mono text-[10px]">{String(c.id).slice(0, 8)}</span>
                    <span className={`font-semibold ${(c.delta as number) > 0 ? "text-emerald-700" : "text-rose-700"}`}>
                      {(c.delta as number) > 0 ? "+" : ""}{String(c.delta)}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
            {(ranking.newCandidateIds as unknown[])?.length ? (
              <div>
                <div className="font-medium text-slate-900 mb-1">New candidates</div>
                {(ranking.newCandidateIds as string[]).map((id) => (
                  <div key={id} className="text-[10px] text-emerald-700 font-mono">{id.slice(0, 12)}…</div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Warnings */}
      {summary.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-1">
          <div className="text-[10px] font-semibold text-amber-700">NOTICES</div>
          {summary.warnings.map((w, i) => (
            <div key={i} className="text-[10px] text-amber-800">{w}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Run list item ──────────────────────────────────────────────────────────────

function RunItem({
  run,
  selected,
  compareSelected,
  onSelect,
  onToggleCompare,
}: {
  run: SavedRunSummary;
  selected: boolean;
  compareSelected: boolean;
  onSelect: () => void;
  onToggleCompare: () => void;
}) {
  return (
    <div
      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
        selected ? "border-indigo-300 bg-indigo-50" : compareSelected ? "border-blue-300 bg-blue-50" : "border-slate-100 bg-white hover:bg-slate-50"
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">
              {TYPE_LABELS[run.runType] ?? run.runType}
            </span>
            {run.finalDecision ? decisionBadge(run.finalDecision) : null}
          </div>
          <div className="text-xs font-medium text-slate-800 truncate mt-0.5">
            {run.label || run.regionName || `${run.latitude?.toFixed(3)}, ${run.longitude?.toFixed(3)}`}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">{formatDate(run.createdAt)}</div>
        </div>
        <div className="shrink-0 text-right">
          {run.totalSuitabilityScore != null && (
            <div className={`text-sm font-bold ${scoreColour(run.totalSuitabilityScore)}`}>
              {run.totalSuitabilityScore.toFixed(0)}
            </div>
          )}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onToggleCompare(); }}
            className={`mt-1 text-[9px] px-1.5 py-0.5 rounded border font-medium transition-colors ${
              compareSelected
                ? "border-blue-300 bg-blue-100 text-blue-700"
                : "border-slate-200 text-slate-400 hover:border-blue-200 hover:text-blue-600"
            }`}
          >
            {compareSelected ? "✓ Comparing" : "Compare"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const [filter, setFilter] = useState<string>("all");
  const [runs, setRuns] = useState<SavedRunSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compareId, setCompareId] = useState<string | null>(null);

  const [comparison, setComparison] = useState<HistorySummaryResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setListLoading(true);
    setListError(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    fetchHistoryRuns(filter === "all" ? undefined : filter, 50, 0, abortRef.current.signal)
      .then((r) => { setRuns(r.runs); setTotal(r.total); })
      .catch((e: unknown) => {
        if ((e as Error)?.name === "AbortError") return;
        setListError(e instanceof Error ? e.message : "Failed to load history");
      })
      .finally(() => setListLoading(false));
  }, [filter]);

  async function handleCompare() {
    if (!selectedId || !compareId) return;
    setCompareError(null);
    setCompareLoading(true);
    setComparison(null);
    try {
      const result = await fetchHistoryCompare(selectedId, compareId);
      setComparison(result);
    } catch (e: unknown) {
      setCompareError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setCompareLoading(false);
    }
  }

  const selectedRun = runs.find((r) => r.id === selectedId);
  const compareRun = runs.find((r) => r.id === compareId);

  return (
    <div className="flex min-h-full flex-col bg-gradient-to-b from-slate-50 via-white to-white">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/70 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-4">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Link href="/" className="text-xs text-slate-500 hover:text-emerald-700">← Home</Link>
              <Link href="/demo" className="text-xs text-slate-500 hover:text-emerald-700">Site Analysis</Link>
              <Link href="/prospecting" className="text-xs text-slate-500 hover:text-emerald-700">Prospecting</Link>
              <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-800">
                History
              </span>
            </div>
            <div className="text-xs font-semibold tracking-[0.18em] text-emerald-700">CHITTA</div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-950">Run History</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {total} saved run{total !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Sidebar: filter + list */}
        <aside className="lg:col-span-4 space-y-3">
          {/* Type filter */}
          <div className="flex flex-wrap gap-1">
            {TYPE_FILTERS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => { setFilter(t); setSelectedId(null); setCompareId(null); setComparison(null); }}
                className={`rounded-lg px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                  filter === t
                    ? "bg-indigo-100 text-indigo-800"
                    : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                }`}
              >
                {t === "all" ? "All" : TYPE_LABELS[t] ?? t}
              </button>
            ))}
          </div>

          {listError && (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800">{listError}</div>
          )}

          {listLoading && (
            <div className="text-xs text-slate-400 px-1">Loading…</div>
          )}

          {/* Compare action */}
          {selectedId && compareId && (
            <button
              type="button"
              onClick={handleCompare}
              disabled={compareLoading}
              className="w-full rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-60"
            >
              {compareLoading ? "Comparing…" : "Run LangGraph Comparison"}
            </button>
          )}

          {selectedId && !compareId && (
            <div className="text-[10px] text-slate-400 px-1">
              Select a second run to compare. Click "Compare" on any run.
            </div>
          )}

          {/* Run list */}
          <div className="space-y-2">
            {runs.map((run) => (
              <RunItem
                key={run.id}
                run={run}
                selected={run.id === selectedId}
                compareSelected={run.id === compareId}
                onSelect={() => {
                  setSelectedId((prev) => prev === run.id ? null : run.id);
                  setComparison(null);
                }}
                onToggleCompare={() => {
                  setCompareId((prev) => prev === run.id ? null : run.id);
                  setComparison(null);
                }}
              />
            ))}
            {!listLoading && runs.length === 0 && (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white/60 p-6 text-center text-xs text-slate-400">
                No runs saved yet. Use "Save to History" on the Site Analysis or Prospecting pages.
              </div>
            )}
          </div>
        </aside>

        {/* Main content */}
        <div className="lg:col-span-8 space-y-4">
          {/* Comparison result */}
          {compareError && (
            <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800">{compareError}</div>
          )}

          {comparison && (
            <div className="chitta-card rounded-xl bg-white p-4 shadow-sm">
              <div className="mb-3 text-xs font-semibold tracking-[0.12em] text-slate-500">COMPARISON RESULT</div>
              <ComparisonPanel summary={comparison} />
            </div>
          )}

          {/* Selected run detail */}
          {selectedRun && !comparison && (
            <div className="chitta-card rounded-xl bg-white p-4 shadow-sm">
              <div className="mb-3 text-xs font-semibold tracking-[0.12em] text-slate-500">SELECTED RUN</div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Type</span>
                  <span className="font-medium">{TYPE_LABELS[selectedRun.runType] ?? selectedRun.runType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Label</span>
                  <span className="font-medium">{selectedRun.label || "—"}</span>
                </div>
                {selectedRun.totalSuitabilityScore != null && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Total suitability</span>
                    <span className={`font-bold ${scoreColour(selectedRun.totalSuitabilityScore)}`}>
                      {selectedRun.totalSuitabilityScore.toFixed(1)}/100
                    </span>
                  </div>
                )}
                {selectedRun.finalDecision && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Decision</span>
                    {decisionBadge(selectedRun.finalDecision)}
                  </div>
                )}
                {selectedRun.regionName && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Region</span>
                    <span className="font-medium">{selectedRun.regionName}</span>
                  </div>
                )}
                {(selectedRun.latitude != null) && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Coordinates</span>
                    <span className="font-medium font-mono text-xs">
                      {selectedRun.latitude.toFixed(4)}, {selectedRun.longitude?.toFixed(4)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-slate-400">Saved</span>
                  <span className="text-xs">{formatDate(selectedRun.createdAt)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Formula</span>
                  <span className="text-xs font-mono">{selectedRun.formulaVersion || "—"}</span>
                </div>
              </div>

              {compareRun && (
                <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3">
                  <div className="text-[10px] font-semibold text-blue-600 mb-1">COMPARING AGAINST</div>
                  <div className="text-xs text-blue-800 font-medium">{compareRun.label || compareRun.regionName}</div>
                  <div className="text-[10px] text-blue-600">{formatDate(compareRun.createdAt)}</div>
                </div>
              )}
            </div>
          )}

          {!selectedId && !comparison && !compareLoading && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white/60 p-10 text-center text-sm text-slate-400">
              Select a run from the list to view details, or select two runs to compare them.
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
