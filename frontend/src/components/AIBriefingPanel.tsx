"use client";

import { LoadingProgress } from "@/components/LoadingProgress";
import { useRef, useState } from "react";
import { runAISynthesis } from "@/lib/api";
import type {
  EvidencePacket,
  ProspectingResponse,
  SimulationResponse,
  SiteAnalysisResponse,
  SynthesisMode,
  SynthesisNarrative,
  SynthesisResponse,
} from "@/lib/types";

// ── Sub-components ─────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="text-[10px] font-semibold tracking-[0.12em] text-slate-500">{title}</div>
      {children}
    </div>
  );
}

function BulletList({ items, tone = "neutral" }: { items: string[]; tone?: "good" | "risk" | "neutral" }) {
  const dot: Record<string, string> = {
    good: "bg-emerald-400",
    risk: "bg-rose-400",
    neutral: "bg-slate-300",
  };
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
          <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot[tone]}`} />
          {item}
        </li>
      ))}
    </ul>
  );
}

function NarrativeBlock({ text }: { text: string }) {
  return <p className="text-xs leading-relaxed text-slate-700">{text}</p>;
}

function EvidenceDrawer({ packets }: { packets: EvidencePacket[] }) {
  const [open, setOpen] = useState(false);

  const byCategory = packets.reduce<Record<string, EvidencePacket[]>>((acc, p) => {
    (acc[p.category] ??= []).push(p);
    return acc;
  }, {});

  const qualityColour: Record<string, string> = {
    measured: "text-emerald-700 bg-emerald-50",
    computed: "text-blue-700 bg-blue-50",
    estimated: "text-amber-700 bg-amber-50",
    unavailable: "text-slate-400 bg-slate-50",
  };

  return (
    <div className="border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-xs font-medium text-slate-500 hover:text-slate-700"
      >
        <span>Evidence packets ({packets.length})</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          {Object.entries(byCategory).map(([cat, evs]) => (
            <div key={cat}>
              <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                {cat}
              </div>
              <div className="space-y-1">
                {evs.map((e) => (
                  <div
                    key={e.evidenceId}
                    className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[10px] font-mono text-slate-400">{e.evidenceId}</div>
                      <div className="text-xs text-slate-700">{e.label}</div>
                      <div className="text-xs font-medium text-slate-900">
                        {e.value}{e.unit ? ` ${e.unit}` : ""}
                      </div>
                      <div className="text-[10px] text-slate-400">{e.source}</div>
                    </div>
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold ${qualityColour[e.quality] ?? "text-slate-500 bg-slate-100"}`}>
                      {e.quality}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CitationsDrawer({ narrative }: { narrative: SynthesisNarrative }) {
  const [open, setOpen] = useState(false);
  const citations = narrative.citations.filter((c) => c.evidenceIds.length > 0);
  if (citations.length === 0) return null;

  return (
    <div className="border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-xs font-medium text-slate-500 hover:text-slate-700"
      >
        <span>Citations ({citations.length})</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="mt-3 space-y-2">
          {citations.map((c, i) => (
            <div key={i} className="rounded-lg border border-slate-100 p-2">
              <div className="text-xs text-slate-700">"{c.claim}"</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {c.evidenceIds.map((eid) => (
                  <span key={eid} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[9px] text-slate-500">
                    {eid}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NarrativePanel({ result }: { result: SynthesisResponse }) {
  const n = result.narrative;

  return (
    <div className="space-y-5">
      {/* Badge */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[10px] font-semibold text-blue-700">
          AI-generated from deterministic CHITTA evidence
        </span>
        <span className="text-[10px] text-slate-400">
          {result.provider} · {result.model}
        </span>
      </div>

      {/* Executive summary */}
      <Section title="EXECUTIVE SUMMARY">
        <NarrativeBlock text={n.executiveSummary} />
      </Section>

      {/* Strategic assessment */}
      <Section title="STRATEGIC ASSESSMENT">
        <NarrativeBlock text={n.strategicAssessment} />
      </Section>

      {/* Signals + risks */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Section title="STRONGEST SIGNALS">
          <BulletList items={n.strongestSignals} tone="good" />
        </Section>
        <Section title="MAJOR RISKS">
          <BulletList items={n.majorRisks} tone="risk" />
        </Section>
      </div>

      {/* Domain narratives */}
      <Section title="ECONOMIC ASSESSMENT">
        <NarrativeBlock text={n.economicNarrative} />
      </Section>
      <Section title="INFRASTRUCTURE ASSESSMENT">
        <NarrativeBlock text={n.infrastructureNarrative} />
      </Section>
      <Section title="ENVIRONMENTAL ASSESSMENT">
        <NarrativeBlock text={n.environmentalNarrative} />
      </Section>

      {/* Recommendations */}
      <Section title="RECOMMENDATIONS">
        <BulletList items={n.recommendations} tone="neutral" />
      </Section>

      {/* Warnings */}
      {n.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="mb-1.5 text-[10px] font-semibold text-amber-700">NOTICES</div>
          <ul className="space-y-1">
            {n.warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-800">{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Validation warnings */}
      {result.validationWarnings.length > 0 && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <div className="mb-1.5 text-[10px] font-semibold text-rose-700">VALIDATION NOTICES</div>
          <ul className="space-y-1">
            {result.validationWarnings.map((w, i) => (
              <li key={i} className="text-xs text-rose-800">{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Citations + Evidence drawers */}
      <CitationsDrawer narrative={n} />
      <EvidenceDrawer packets={result.evidencePackets} />

      {/* Metadata */}
      <div className="text-[10px] text-slate-400">
        Synthesis ID: {result.synthesisId} · Generated: {new Date(result.generatedAt).toLocaleString()}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

type AIBriefingPanelProps = {
  mode: SynthesisMode;
  siteAnalysis?: SiteAnalysisResponse | null;
  prospecting?: ProspectingResponse | null;
  simulation?: SimulationResponse | null;
  onResult?: (result: SynthesisResponse) => void;
};

export function AIBriefingPanel({
  mode,
  siteAnalysis,
  prospecting,
  simulation,
  onResult,
}: AIBriefingPanelProps) {
  const [result, setResult] = useState<SynthesisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleGenerate() {
    setError(null);
    setLoading(true);
    setResult(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await runAISynthesis(
        {
          mode,
          siteAnalysis: siteAnalysis ?? null,
          prospecting: prospecting ?? null,
          simulation: simulation ?? null,
        },
        abortRef.current.signal,
      );
      setResult(res);
      onResult?.(res);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chitta-panel overflow-hidden">
      <div className="border-b border-[var(--chitta-border)] bg-[var(--chitta-bg)] px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--chitta-accent)]">
              AI Briefing
            </p>
            <div className="text-sm font-semibold text-[var(--chitta-ink)]">Grounded synthesis</div>
          </div>
          <button
            type="button"
            onClick={result ? () => setResult(null) : handleGenerate}
            disabled={loading}
            className={`rounded-xl px-4 py-2 text-sm font-semibold shadow-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
              result
                ? "border border-[var(--chitta-border)] bg-[var(--chitta-surface)] text-[var(--chitta-muted)] hover:bg-[var(--chitta-bg)]"
                : "bg-[var(--chitta-accent)] text-white hover:bg-[var(--chitta-accent-hover)]"
            }`}
          >
            {loading ? "Generating briefing…" : result ? "Clear" : "Generate AI Briefing"}
          </button>
        </div>
      </div>

      <div className="px-4 py-4">
        {error && (
          <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800">{error}</div>
        )}

        {!result && !loading && !error && (
          <p className="text-xs text-slate-400">
            Generate a consultant-style AI briefing synthesised from CHITTA&rsquo;s deterministic evidence.
            No invented data — every claim is cited from the analysis.
          </p>
        )}

        {loading && <LoadingProgress variant="ai-briefing" compact />}

        {result && <NarrativePanel result={result} />}
      </div>
    </div>
  );
}
