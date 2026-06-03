"use client";

import { ReactNode } from "react";

export function ScoreCard({
  title,
  value,
  subtitle,
  tone = "neutral",
  icon,
  loading = false,
}: {
  title: string;
  value: string;
  subtitle?: string;
  tone?: "neutral" | "good" | "warn";
  icon?: ReactNode;
  loading?: boolean;
}) {
  const accentBar =
    tone === "good"
      ? "border-t-[var(--chitta-accent)]"
      : tone === "warn"
        ? "border-t-amber-400"
        : "border-t-transparent";

  const toneClasses =
    tone === "good"
      ? "bg-[var(--chitta-accent-soft)]/50 text-[var(--chitta-ink)]"
      : tone === "warn"
        ? "bg-amber-50 text-amber-950"
        : "bg-[var(--chitta-surface)] text-[var(--chitta-ink)]";

  return (
    <div
      className={`rounded-xl border border-[var(--chitta-border)] border-t-2 p-3 ${accentBar} ${toneClasses} flex flex-col gap-0.5 ${loading ? "chitta-score-skeleton pointer-events-none" : ""}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--chitta-muted)]">
          {title}
        </div>
        {icon ? <div className="text-[var(--chitta-muted)]">{icon}</div> : null}
      </div>
      <div className="chitta-mono text-xl font-bold tracking-tight">{value}</div>
      {subtitle ? (
        <div className="text-[10px] leading-snug text-[var(--chitta-muted)]">{subtitle}</div>
      ) : null}
    </div>
  );
}
