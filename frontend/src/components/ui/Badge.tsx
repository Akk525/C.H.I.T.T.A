import type { ReactNode } from "react";

type Tone = "accent" | "sky" | "neutral" | "success" | "warn" | "danger" | "indigo";

const TONES: Record<Tone, string> = {
  accent: "bg-[var(--chitta-accent-soft)] text-[var(--chitta-accent-hover)]",
  sky: "bg-[var(--chitta-sky-soft)] text-sky-700",
  neutral: "bg-slate-100 text-slate-600",
  success: "bg-emerald-100 text-emerald-800",
  warn: "bg-amber-100 text-amber-800",
  danger: "bg-rose-100 text-rose-800",
  indigo: "bg-indigo-100 text-indigo-800",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
