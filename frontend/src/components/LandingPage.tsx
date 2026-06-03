"use client";

import Link from "next/link";
import { SampleSiteButtons } from "@/components/SampleSiteButtons";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { MetricStrip } from "@/components/ui/MetricStrip";
import { SectionLabel } from "@/components/ui/SectionLabel";

function MapMockIllustration() {
  const cells = [
    "bg-teal-200/70",
    "bg-sky-200/60",
    "bg-emerald-300/50",
    "bg-sky-100/80",
    "bg-teal-400/60",
    "bg-emerald-200/70",
    "bg-slate-100/90",
    "bg-teal-300/55",
    "bg-sky-300/50",
    "bg-emerald-300/45",
    "bg-teal-200/65",
    "bg-sky-200/55",
    "bg-teal-500/50",
    "bg-emerald-200/60",
    "bg-sky-100/70",
    "bg-teal-300/40",
  ];
  return (
    <div
      className="relative mb-3 h-36 overflow-hidden rounded-lg ring-1 ring-white/70"
      aria-hidden="true"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-[#e8f4f8] via-[#d4ebe3] to-[#c5e8dc]" />
      <div className="absolute inset-0 grid grid-cols-4 grid-rows-4 gap-px p-1 opacity-90">
        {cells.map((cls, i) => (
          <div key={i} className={`rounded-sm ${cls}`} />
        ))}
      </div>
      <svg className="absolute inset-0 h-full w-full opacity-20" viewBox="0 0 200 144" preserveAspectRatio="none">
        <path d="M0 80 Q50 60 100 90 T200 70" fill="none" stroke="#0d9488" strokeWidth="1.5" />
        <path d="M0 110 Q80 95 200 100" fill="none" stroke="#38bdf8" strokeWidth="1" />
      </svg>
      <div className="absolute left-[52%] top-[42%] flex -translate-x-1/2 -translate-y-full flex-col items-center">
        <div className="rounded-full bg-[var(--chitta-accent)] p-1.5 shadow-md ring-2 ring-white">
          <svg className="h-3 w-3 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
          </svg>
        </div>
        <div className="mt-0.5 h-2 w-2 rotate-45 bg-[var(--chitta-accent)]" />
      </div>
      <div className="absolute bottom-2 left-2 rounded bg-white/85 px-1.5 py-0.5 text-[8px] font-medium text-[var(--chitta-muted)] shadow-sm">
        Suitability heatmap · 5×5
      </div>
    </div>
  );
}

function ProductMock() {
  return (
    <div className="chitta-panel chitta-lift relative overflow-hidden rounded-2xl p-1">
      <div className="rounded-xl bg-gradient-to-br from-slate-100 via-[var(--chitta-sky-soft)] to-[var(--chitta-accent-soft)] p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--chitta-muted)]">
            Site Explorer
          </span>
          <Badge tone="success">Promising</Badge>
        </div>
        <MapMockIllustration />
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "Wind", score: "78", sub: "NASA POWER" },
            { label: "Terrain", score: "71", sub: "SRTM 90m" },
            { label: "Total", score: "74", sub: "v2.0" },
          ].map((m) => (
            <div
              key={m.label}
              className="rounded-lg bg-white/90 px-2 py-2 shadow-sm ring-1 ring-[var(--chitta-border)]"
            >
              <div className="text-[9px] font-medium text-[var(--chitta-muted)]">{m.label}</div>
              <div className="chitta-mono text-lg font-bold text-[var(--chitta-ink)]">{m.score}</div>
              <div className="text-[8px] text-[var(--chitta-accent)]">{m.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BentoFeature({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="chitta-panel chitta-lift rounded-2xl p-5">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--chitta-accent-soft)] text-[var(--chitta-accent)]">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-[var(--chitta-ink)]">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-[var(--chitta-muted)]">{description}</p>
    </div>
  );
}

const WORKFLOW = [
  { step: "01", title: "Select a site", body: "Search globally or load a curated Indian wind corridor." },
  { step: "02", title: "Analyze", body: "NASA POWER wind + OpenTopoData elevation with deterministic scoring." },
  { step: "03", title: "Heatmap", body: "Screen a radius and rank top candidate zones." },
  { step: "04", title: "Export", body: "PDF dossier with methodology audit trail." },
];

const BENTO = [
  {
    title: "Multi-agent scoring",
    description: "Wind, terrain, infrastructure, environmental, and social agents with a coordinator verdict.",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.59.659H9.06a2.25 2.25 0 01-1.59-.659L5 14.5" />
      </svg>
    ),
  },
  {
    title: "Suitability heatmaps",
    description: "N×N grid scoring with top-zone ranking and map overlays.",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
    ),
  },
  {
    title: "AI briefing",
    description: "Grounded LLM narratives with citations — every claim tied to evidence packets.",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    ),
  },
  {
    title: "PDF export",
    description: "Consultant-style site and prospecting dossiers ready for stakeholders.",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 18H15a2.25 2.25 0 002.25-2.25V9.75a2.25 2.25 0 00-2.25-2.25H8.25A2.25 2.25 0 006 9.75v10.5A2.25 2.25 0 008.25 22.5z" />
      </svg>
    ),
  },
  {
    title: "Audit trail",
    description: "analysisId, formula version, and step-by-step methodology metadata.",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
  },
  {
    title: "LangGraph compare",
    description: "Save runs and generate narrative deltas between historical analyses.",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
  },
];

export function LandingPage() {
  return (
    <div className="min-h-full bg-[var(--chitta-bg)]">
      <header className="sticky top-0 z-40 border-b border-[var(--chitta-border)] bg-[var(--chitta-surface)]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--chitta-accent)] text-sm font-bold text-white">
              C
            </span>
            <span className="text-sm font-semibold text-[var(--chitta-ink)]">CHITTA</span>
          </Link>
          <nav className="hidden gap-6 text-sm text-[var(--chitta-muted)] sm:flex">
            <a href="#features" className="hover:text-[var(--chitta-accent)]">Features</a>
            <a href="#workflow" className="hover:text-[var(--chitta-accent)]">Workflow</a>
            <a href="#demo-sites" className="hover:text-[var(--chitta-accent)]">Demo sites</a>
            <Link href="/prospecting" className="hover:text-[var(--chitta-accent)]">Prospecting</Link>
          </nav>
          <Button href="/demo">Launch demo</Button>
        </div>
      </header>

      <main>
        <section className="chitta-hero-glow chitta-grain border-b border-[var(--chitta-border)]">
          <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:py-24 lg:grid-cols-2 lg:items-center">
            <div>
              <SectionLabel>Terrain intelligence for wind developers</SectionLabel>
              <h1 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight text-[var(--chitta-ink)] sm:text-5xl lg:text-[3.25rem]">
                Screen wind sites in minutes, not months.
              </h1>
              <p className="mt-6 max-w-xl text-base leading-7 text-[var(--chitta-muted)] sm:text-lg">
                CHITTA fuses live wind and elevation data with multi-agent scoring, suitability heatmaps,
                and audit-ready reports — so your team spends field budget on the right coordinates.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button href="/demo">Launch demo</Button>
                <Button href="#demo-sites" variant="secondary">
                  Try a sample site
                </Button>
              </div>
            </div>
            <ProductMock />
          </div>
        </section>

        <section className="border-b border-[var(--chitta-border)] bg-[var(--chitta-surface)] py-12">
          <div className="mx-auto max-w-6xl px-4">
            <MetricStrip
              items={[
                { value: "6", label: "Scoring dimensions" },
                { value: "5", label: "Specialist agents" },
                { value: "REAL", label: "NASA POWER + SRTM" },
                { value: "100%", label: "Audit trail coverage" },
              ]}
            />
          </div>
        </section>

        <section id="features" className="py-16 sm:py-20 scroll-mt-20">
          <div className="mx-auto max-w-6xl px-4">
            <SectionLabel>Platform</SectionLabel>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--chitta-ink)] sm:text-3xl">
              Everything for first-pass wind diligence
            </h2>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {BENTO.map((f) => (
                <BentoFeature key={f.title} {...f} />
              ))}
            </div>
          </div>
        </section>

        <section id="workflow" className="border-y border-[var(--chitta-border)] bg-[var(--chitta-surface)] py-16 scroll-mt-20">
          <div className="mx-auto max-w-6xl px-4">
            <SectionLabel>Workflow</SectionLabel>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--chitta-ink)]">Four steps to a defensible score</h2>
            <div className="mt-10 hidden sm:flex sm:items-start sm:justify-between sm:gap-2">
              {WORKFLOW.map((w, i) => (
                <div key={w.step} className="relative flex-1 text-center">
                  {i < WORKFLOW.length - 1 ? (
                    <div className="absolute left-[calc(50%+24px)] right-0 top-5 h-px bg-[var(--chitta-border)]" />
                  ) : null}
                  <div className="chitta-mono mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-[var(--chitta-accent)] text-sm font-bold text-white">
                    {w.step}
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-[var(--chitta-ink)]">{w.title}</h3>
                  <p className="mt-1 px-2 text-xs text-[var(--chitta-muted)]">{w.body}</p>
                </div>
              ))}
            </div>
            <div className="mt-8 grid gap-3 sm:hidden">
              {WORKFLOW.map((w) => (
                <div key={w.step} className="chitta-panel rounded-xl p-4">
                  <span className="chitta-mono text-xs font-bold text-[var(--chitta-accent)]">{w.step}</span>
                  <h3 className="mt-1 font-semibold text-[var(--chitta-ink)]">{w.title}</h3>
                  <p className="mt-1 text-sm text-[var(--chitta-muted)]">{w.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-12">
          <div className="mx-auto max-w-6xl px-4">
            <SectionLabel>Data sources</SectionLabel>
            <div className="mt-4 flex flex-wrap gap-2">
              {["NASA POWER", "OpenTopoData SRTM", "OpenStreetMap", "GDELT signals"].map((src) => (
                <span
                  key={src}
                  className="rounded-full border border-[var(--chitta-border)] bg-[var(--chitta-surface)] px-4 py-2 text-sm font-medium text-[var(--chitta-ink)] shadow-sm"
                >
                  {src}
                </span>
              ))}
            </div>
            <p className="mt-6 max-w-3xl text-sm leading-7 text-[var(--chitta-muted)]">
              Every analysis returns an <code className="chitta-mono rounded bg-slate-100 px-1.5 py-0.5 text-xs">analysisId</code>,
              methodology metadata, and a step-by-step audit trail. Mock fallbacks are clearly labeled when APIs are unavailable.
            </p>
          </div>
        </section>

        <section id="demo-sites" className="scroll-mt-20 border-y border-[var(--chitta-border)] bg-[var(--chitta-accent-soft)]/30 py-16">
          <div className="mx-auto max-w-6xl px-4">
            <SectionLabel>Live demo</SectionLabel>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--chitta-ink)]">Jump into India&apos;s wind corridors</h2>
            <p className="mt-3 max-w-2xl text-sm text-[var(--chitta-muted)]">
              Pre-selected screening locations — each opens the map, runs analysis, and supports heatmap generation.
            </p>
            <div className="chitta-panel mt-8 rounded-2xl p-6">
              <SampleSiteButtons linkMode />
            </div>
          </div>
        </section>

        <section id="demo-path" className="py-16 scroll-mt-20">
          <div className="mx-auto max-w-6xl px-4">
            <SectionLabel>Recommended path</SectionLabel>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--chitta-ink)]">
              Seven steps from coordinates to investment insight
            </h2>
            <p className="mt-3 max-w-2xl text-sm text-[var(--chitta-muted)]">
              Full workflow: site analysis → prospecting → simulation → layout → AI briefing → PDF → history compare.
            </p>
            <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[
                "Pick Karnataka Wind Corridor in Site Analysis",
                "Run Prospecting on the same region",
                "Open Scenario Simulation on top candidates",
                "Generate turbine layout with wake estimates",
                "Create a grounded AI briefing",
                "Export the prospecting PDF dossier",
                "Save runs and LangGraph-compare in History",
              ].map((text, i) => (
                <li key={text} className="chitta-panel flex gap-3 rounded-xl p-4">
                  <span className="chitta-mono flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--chitta-accent-soft)] text-xs font-bold text-[var(--chitta-accent)]">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-sm text-[var(--chitta-muted)]">{text}</span>
                </li>
              ))}
            </ol>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button href="/demo">Start site analysis</Button>
              <Button href="/prospecting" variant="secondary">Open prospecting</Button>
            </div>
          </div>
        </section>

        <section className="bg-[var(--chitta-accent)] py-16">
          <div className="mx-auto max-w-6xl px-4 text-center">
            <h2 className="text-2xl font-semibold text-white sm:text-3xl">
              Ready to evaluate your next candidate site?
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-sm text-teal-100">
              Launch the live demo — analyze coordinates, rank zones, and export a consultant PDF in one session.
            </p>
            <Button
              href="/demo"
              variant="secondary"
              className="mt-8 !border-white !bg-white !text-[var(--chitta-accent)] hover:!bg-teal-50"
            >
              Launch demo
            </Button>
          </div>
        </section>

        <section className="py-12">
          <div className="mx-auto max-w-6xl px-4">
            <div className="chitta-panel rounded-2xl bg-slate-50 p-6 text-sm leading-6 text-[var(--chitta-muted)]">
              <strong className="text-[var(--chitta-ink)]">Disclaimer:</strong> CHITTA is preliminary screening only — not a bankable resource assessment or engineering recommendation. Validate with on-site measurement and professional due diligence.
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--chitta-border)] py-8 text-center text-xs text-[var(--chitta-muted)]">
        CHITTA — Climate Heuristics &amp; Intelligent Turbine Terrain Analysis
      </footer>
    </div>
  );
}
