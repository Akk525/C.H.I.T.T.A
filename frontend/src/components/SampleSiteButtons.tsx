"use client";

import Link from "next/link";
import { DEMO_SITES, type DemoSite } from "@/lib/demoSites";

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
    <div className={compact ? "flex flex-wrap gap-2" : "grid gap-2 sm:grid-cols-3"}>
      {DEMO_SITES.map((site) => {
        const active = activeId === site.id;
        const className = `rounded-xl border px-3 py-2 text-left transition-colors ${
          active
            ? "border-emerald-300 bg-emerald-50"
            : "border-slate-200 bg-white hover:border-emerald-200 hover:bg-emerald-50/50"
        } ${compact ? "text-xs" : "text-sm"}`;

        const inner = (
          <>
            <div className="font-medium text-slate-900">{site.label}</div>
            {!compact ? (
              <div className="mt-1 text-xs text-slate-600">{site.description}</div>
            ) : null}
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
          <button
            key={site.id}
            type="button"
            onClick={() => onSelect?.(site)}
            className={className}
          >
            {inner}
          </button>
        );
      })}
    </div>
  );
}
