"use client";

import Link from "next/link";
import { DEMO_SITES, type DemoSite } from "@/lib/demoSites";

function PinIcon() {
  return (
    <svg className="h-4 w-4 shrink-0 text-[var(--chitta-accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
    </svg>
  );
}

export function SampleSiteButtons({
  onSelect,
  activeId,
  compact = false,
  linkMode = false,
}: {
  onSelect?: (site: DemoSite) => void;
  activeId?: string | null;
  compact?: boolean;
  linkMode?: boolean;
}) {
  return (
    <div className={compact ? "flex flex-wrap gap-2" : "grid gap-3 sm:grid-cols-3"}>
      {DEMO_SITES.map((site) => {
        const active = activeId === site.id;
        const className = `chitta-lift flex gap-2 rounded-xl border px-3 py-2.5 text-left transition-colors ${
          active
            ? "border-[var(--chitta-accent)] bg-[var(--chitta-accent-soft)] ring-1 ring-[var(--chitta-accent)]/30"
            : "border-[var(--chitta-border)] bg-[var(--chitta-surface)] hover:border-[var(--chitta-accent)]/40 hover:bg-[var(--chitta-bg)]"
        } ${compact ? "text-xs" : "text-sm"}`;

        const inner = (
          <>
            <PinIcon />
            <div className="min-w-0">
              <div className="font-semibold text-[var(--chitta-ink)]">{site.label}</div>
              {!compact ? (
                <div className="mt-0.5 text-xs text-[var(--chitta-muted)]">{site.description}</div>
              ) : null}
            </div>
          </>
        );

        if (linkMode) {
          return (
            <Link key={site.id} href={`/demo?sample=${site.id}`} className={className}>
              {inner}
            </Link>
          );
        }

        return (
          <button key={site.id} type="button" onClick={() => onSelect?.(site)} className={className}>
            {inner}
          </button>
        );
      })}
    </div>
  );
}
