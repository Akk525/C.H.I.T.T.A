"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Badge } from "./Badge";
import { Button } from "./Button";

const NAV = [
  { href: "/demo", label: "Site Analysis", match: "/demo", badge: "Demo" as const },
  { href: "/prospecting", label: "Prospecting", match: "/prospecting", badge: "Prospecting" as const },
  { href: "/history", label: "History", match: "/history", badge: "History" as const },
];

const BADGE_TONE = {
  Demo: "accent",
  Prospecting: "sky",
  History: "indigo",
} as const;

export function AppShell({
  children,
  header,
}: {
  children: ReactNode;
  header?: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-full flex-col bg-[var(--chitta-bg)]">
      <header className="sticky top-0 z-40 border-b border-[var(--chitta-border)] bg-[var(--chitta-surface)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-8">
            <Link href="/" className="group flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--chitta-accent)] text-xs font-bold text-white shadow-sm">
                C
              </span>
              <span className="text-sm font-semibold tracking-tight text-[var(--chitta-ink)] group-hover:text-[var(--chitta-accent)]">
                CHITTA
              </span>
            </Link>
            <nav className="hidden items-center gap-1 md:flex">
              {NAV.map((item) => {
                const active = pathname.startsWith(item.match);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`relative rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      active
                        ? "text-[var(--chitta-accent)]"
                        : "text-[var(--chitta-muted)] hover:text-[var(--chitta-ink)]"
                    }`}
                  >
                    {item.label}
                    {active ? (
                      <span className="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-[var(--chitta-accent)]" />
                    ) : null}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            {NAV.map((item) => {
              if (!pathname.startsWith(item.match)) return null;
              return (
                <Badge
                  key={item.href}
                  tone={BADGE_TONE[item.badge] as "accent" | "sky" | "indigo"}
                  className="hidden sm:inline-flex"
                >
                  {item.badge}
                </Badge>
              );
            })}
            <Button href="/" variant="ghost" className="hidden sm:inline-flex py-2">
              Home
            </Button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-[var(--chitta-border)] px-4 py-2 md:hidden">
          {NAV.map((item) => {
            const active = pathname.startsWith(item.match);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium ${
                  active
                    ? "bg-[var(--chitta-accent-soft)] text-[var(--chitta-accent)]"
                    : "text-[var(--chitta-muted)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      {header ? (
        <div className="border-b border-[var(--chitta-border)] bg-[var(--chitta-surface)]">
          <div className="mx-auto max-w-7xl px-4 py-4">{header}</div>
        </div>
      ) : null}

      <div className="flex-1">{children}</div>
    </div>
  );
}
