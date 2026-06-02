"use client";

import { ReactNode } from "react";

export function ScoreCard({
  title,
  value,
  subtitle,
  tone = "neutral",
  icon,
}: {
  title: string;
  value: string;
  subtitle?: string;
  tone?: "neutral" | "good" | "warn";
  icon?: ReactNode;
}) {
  const toneClasses =
    tone === "good"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : tone === "warn"
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : "border-slate-200 bg-white text-slate-900";

  return (
    <div
      className={`chitta-card rounded-xl p-4 shadow-sm ${toneClasses} flex flex-col gap-1`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-slate-700">{title}</div>
        {icon ? <div className="text-slate-500">{icon}</div> : null}
      </div>
      <div className="text-2xl font-semibold tracking-tight">{value}</div>
      {subtitle ? (
        <div className="text-xs text-slate-600">{subtitle}</div>
      ) : null}
    </div>
  );
}

