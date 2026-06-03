import type { ReactNode } from "react";
import { SectionLabel } from "./SectionLabel";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  badge,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  badge?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? <SectionLabel>{eyebrow}</SectionLabel> : null}
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-tight text-[var(--chitta-ink)] sm:text-2xl">
            {title}
          </h1>
          {badge}
        </div>
        {subtitle ? (
          <p className="mt-1 max-w-2xl text-sm text-[var(--chitta-muted)]">{subtitle}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
