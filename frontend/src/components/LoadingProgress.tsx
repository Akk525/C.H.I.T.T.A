"use client";

import { useEffect, useState } from "react";

export type LoadingVariant =
  | "site-analysis"
  | "heatmap"
  | "prospecting"
  | "simulation"
  | "ai-briefing"
  | "signals"
  | "layout"
  | "export-pdf";

type VariantConfig = {
  title: string;
  subtitle: string;
  steps: string[];
};

const VARIANT_CONFIG: Record<LoadingVariant, VariantConfig> = {
  "site-analysis": {
    title: "Analyzing site",
    subtitle: "Fetching live geospatial data and building your assessment",
    steps: [
      "Querying NASA POWER for hub-height wind speeds…",
      "Fetching SRTM elevation from OpenTopoData…",
      "Scanning OpenStreetMap for roads and transmission…",
      "Estimating land cover and settlement density…",
      "Running multi-agent suitability scoring…",
      "Composing consultant report and audit trail…",
    ],
  },
  heatmap: {
    title: "Building suitability heatmap",
    subtitle: "Scoring each grid cell across the study area",
    steps: [
      "Sampling wind and terrain for grid cells…",
      "Computing per-cell suitability scores…",
      "Ranking top candidate zones…",
    ],
  },
  prospecting: {
    title: "Regional prospecting",
    subtitle: "Batch screening candidate sites in your study region",
    steps: [
      "Pass 1: quick wind and terrain screen across the grid…",
      "Selecting top candidates for full enrichment…",
      "Pass 2: infrastructure, environmental, and social agents…",
      "Clustering high-potential zones…",
      "Finalizing run summary and audit trail…",
    ],
  },
  simulation: {
    title: "Running scenario",
    subtitle: "Recomputing scores with your weight and economic assumptions",
    steps: [
      "Applying scenario weight adjustments…",
      "Recalculating suitability and economics…",
      "Building comparison deltas…",
    ],
  },
  "ai-briefing": {
    title: "Generating AI briefing",
    subtitle: "Synthesizing narrative strictly from deterministic evidence",
    steps: [
      "Packaging evidence from analysis outputs…",
      "Calling configured LLM (Claude, Gemini, or mock)…",
      "Validating citations against evidence packets…",
    ],
  },
  signals: {
    title: "Querying development signals",
    subtitle: "Searching regional news for advisory intelligence",
    steps: [
      "Querying GDELT document API…",
      "Filtering renewable and grid-related articles…",
      "Summarizing signals for the region…",
    ],
  },
  layout: {
    title: "Generating turbine layout",
    subtitle: "Placing turbines and estimating wake losses",
    steps: [
      "Aligning grid to prevailing wind direction…",
      "Placing turbine positions…",
      "Computing Jensen/Park wake losses…",
    ],
  },
  "export-pdf": {
    title: "Building PDF report",
    subtitle: "Rendering charts, scores, and narrative into a downloadable dossier",
    steps: [
      "Formatting assessment sections…",
      "Embedding scores and methodology…",
      "Generating PDF document…",
    ],
  },
};

type Props = {
  variant: LoadingVariant;
  /** Optional extra line (e.g. candidate count, region name). */
  detail?: string;
  /** Smaller inline layout for panels and secondary actions. */
  compact?: boolean;
  className?: string;
};

export function LoadingProgress({ variant, detail, compact = false, className = "" }: Props) {
  const config = VARIANT_CONFIG[variant];
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setStepIndex((i) => (i + 1) % config.steps.length);
    }, 2400);
    return () => window.clearInterval(id);
  }, [variant, config.steps.length]);

  const currentStep = config.steps[stepIndex] ?? config.steps[0];

  if (compact) {
    return (
      <div
        className={`rounded-lg border border-[var(--chitta-border)] bg-[var(--chitta-accent-soft)]/60 px-3 py-2.5 ${className}`}
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <div className="chitta-progress-track mb-2" aria-hidden="true">
          <div className="chitta-progress-bar" />
        </div>
        <p className="text-xs font-medium text-[var(--chitta-ink)]">{config.title}</p>
        <p className="mt-0.5 text-[11px] text-[var(--chitta-muted)] transition-opacity duration-300">
          {currentStep}
        </p>
      </div>
    );
  }

  return (
    <div
      className={`chitta-panel bg-gradient-to-br from-[var(--chitta-accent-soft)]/40 via-[var(--chitta-surface)] to-[var(--chitta-surface)] p-5 ${className}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex items-start gap-3">
        <div
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--chitta-accent-soft)]"
          aria-hidden="true"
        >
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-teal-200 border-t-[var(--chitta-accent)]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[var(--chitta-ink)]">{config.title}</p>
          <p className="mt-0.5 text-xs text-[var(--chitta-muted)]">{config.subtitle}</p>
          {detail ? (
            <p className="mt-1 text-xs font-medium text-[var(--chitta-accent)]">{detail}</p>
          ) : null}
        </div>
      </div>

      <div className="chitta-progress-track mt-4" aria-hidden="true">
        <div className="chitta-progress-bar" />
      </div>

      <p className="mt-3 text-xs text-[var(--chitta-muted)] transition-opacity duration-300">
        <span className="font-medium text-[var(--chitta-ink)]">Now: </span>
        {currentStep}
      </p>

      <p className="mt-2 text-[10px] text-[var(--chitta-muted)]">
        This usually takes a few seconds — external APIs may add delay.
      </p>
    </div>
  );
}
