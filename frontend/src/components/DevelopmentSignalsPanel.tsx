"use client";

import { LoadingProgress } from "@/components/LoadingProgress";
import { useRef, useState } from "react";
import { queryDevelopmentSignals } from "@/lib/api";
import type { DevelopmentSignal, GroupedInsight, SignalsQueryResponse } from "@/lib/types";

// ── Helpers ────────────────────────────────────────────────────────────────────

const SENTIMENT_STYLES: Record<string, string> = {
  positive: "bg-emerald-100 text-emerald-800",
  negative: "bg-rose-100 text-rose-800",
  mixed:    "bg-amber-100 text-amber-800",
  neutral:  "bg-slate-100 text-slate-600",
};

const CATEGORY_ICON: Record<string, string> = {
  renewable:      "⚡",
  grid:           "🔌",
  infrastructure: "🛣️",
  environmental:  "🌿",
  policy:         "📋",
  economic:       "📈",
};

function SentimentBadge({ sentiment }: { sentiment: string }) {
  return (
    <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${SENTIMENT_STYLES[sentiment] ?? SENTIMENT_STYLES.neutral}`}>
      {sentiment}
    </span>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function InsightCard({ insight }: { insight: GroupedInsight }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
      <span className="mt-0.5 text-base">{CATEGORY_ICON[insight.category] ?? "•"}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-medium text-slate-800">{insight.categoryLabel}</span>
          <SentimentBadge sentiment={insight.sentiment} />
          <span className="text-[10px] text-slate-400">{insight.signalCount} signal{insight.signalCount !== 1 ? "s" : ""}</span>
        </div>
        <div className="text-[10px] text-slate-500 mt-0.5">{insight.keyTheme}</div>
      </div>
    </div>
  );
}

function SignalRow({ signal }: { signal: DevelopmentSignal }) {
  const date = new Date(signal.publishedAt).toLocaleDateString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
  });
  return (
    <div className="border-b border-slate-50 py-2 last:border-0">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0 text-sm">{CATEGORY_ICON[signal.category] ?? "•"}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <SentimentBadge sentiment={signal.sentiment} />
            <span className="text-[10px] text-slate-400">{signal.source}</span>
            <span className="text-[10px] text-slate-300">·</span>
            <span className="text-[10px] text-slate-400">{date}</span>
            <span className="text-[10px] text-slate-300">·</span>
            <span className="text-[10px] text-slate-400">relevance {(signal.relevanceScore * 100).toFixed(0)}%</span>
          </div>
          {signal.url ? (
            <a
              href={signal.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-slate-800 hover:text-emerald-700 hover:underline mt-0.5 block"
            >
              {signal.title}
            </a>
          ) : (
            <div className="text-xs text-slate-800 mt-0.5">{signal.title}</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultsPanel({ result }: { result: SignalsQueryResponse }) {
  const [showAll, setShowAll] = useState(false);
  const visibleSignals = showAll ? result.signals : result.signals.slice(0, 6);

  return (
    <div className="space-y-4">
      {/* Provider badge */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${
          result.provider === "gdelt"
            ? "bg-blue-100 text-blue-700"
            : "bg-slate-100 text-slate-600"
        }`}>
          {result.provider === "gdelt" ? "Live GDELT data" : "Mock signals (dev mode)"}
        </span>
        <span className="text-[10px] text-slate-400">
          {result.signals.length} signals · {new Date(result.generatedAt).toLocaleString()}
        </span>
      </div>

      {/* Agent summary */}
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-3">
        <div className="text-[10px] font-semibold tracking-[0.1em] text-blue-600 mb-1.5">
          DEVELOPMENT SIGNALS AGENT
        </div>
        <p className="text-xs leading-relaxed text-blue-900">{result.agentSummary}</p>
      </div>

      {/* Grouped insights */}
      {result.groupedInsights.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold tracking-[0.1em] text-slate-400 mb-2">BY CATEGORY</div>
          <div className="space-y-1.5">
            {result.groupedInsights.map((g) => (
              <InsightCard key={g.category} insight={g} />
            ))}
          </div>
        </div>
      )}

      {/* Signal list */}
      {result.signals.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold tracking-[0.1em] text-slate-400 mb-1">
            SIGNALS (sorted by relevance)
          </div>
          <div>
            {visibleSignals.map((s) => (
              <SignalRow key={s.id} signal={s} />
            ))}
          </div>
          {result.signals.length > 6 && (
            <button
              type="button"
              onClick={() => setShowAll((v) => !v)}
              className="mt-2 text-[10px] font-medium text-slate-500 hover:text-slate-700"
            >
              {showAll ? "Show fewer" : `Show all ${result.signals.length} signals`}
            </button>
          )}
        </div>
      )}

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-1">
          <div className="text-[10px] font-semibold text-amber-700">NOTICES</div>
          {result.warnings.map((w, i) => (
            <div key={i} className="text-[10px] text-amber-800">{w}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

type Props = {
  regionName: string;
  latitude: number;
  longitude: number;
  radiusKm?: number;
};

export function DevelopmentSignalsPanel({ regionName, latitude, longitude, radiusKm = 100 }: Props) {
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<SignalsQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleQuery() {
    setError(null);
    setLoading(true);
    setResult(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await queryDevelopmentSignals(
        { regionName, latitude, longitude, radiusKm },
        abortRef.current.signal,
      );
      setResult(res);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Signals query failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chitta-card rounded-xl bg-white shadow-sm">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <div className="text-xs font-semibold tracking-[0.12em] text-slate-500">DEVELOPMENT SIGNALS</div>
          <div className="text-sm font-medium text-slate-900">Regional Intelligence</div>
          <div className="text-xs text-slate-400">GDELT news signals · advisory only</div>
        </div>
        <div className="flex items-center gap-2">
          {result && (
            <span className="text-[10px] text-slate-400">{result.signals.length} signals</span>
          )}
          <span className="text-slate-400">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3 space-y-4">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleQuery}
              disabled={loading}
              className="flex-1 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Querying signals…" : result ? "Refresh Signals" : "Query Development Signals"}
            </button>
            {result && (
              <button
                type="button"
                onClick={() => setResult(null)}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50"
              >
                Clear
              </button>
            )}
          </div>

          <div className="text-[10px] text-slate-400 leading-relaxed">
            Searches GDELT news database for regional development signals: renewable energy activity,
            grid expansion, policy announcements, and environmental factors.
            Results are <strong>advisory only</strong> and not verified facts.
          </div>

          {loading && <LoadingProgress variant="signals" compact />}

          {error && (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800">{error}</div>
          )}

          {result && <ResultsPanel result={result} />}
        </div>
      )}
    </div>
  );
}
