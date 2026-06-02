"use client";

import Link from "next/link";
import { SampleSiteButtons } from "@/components/SampleSiteButtons";

function Section({
  id,
  title,
  children,
}: {
  id?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 py-12 sm:py-16">
      <div className="mx-auto max-w-5xl px-4">
        <h2 className="text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          {title}
        </h2>
        <div className="mt-4 text-sm leading-7 text-slate-600 sm:text-base">{children}</div>
      </div>
    </section>
  );
}

function WorkflowStep({ step, title, body }: { step: string; title: string; body: string }) {
  return (
    <div className="chitta-card rounded-xl bg-white p-5 shadow-sm">
      <div className="text-xs font-semibold tracking-[0.14em] text-emerald-700">STEP {step}</div>
      <h3 className="mt-2 text-base font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-full bg-gradient-to-b from-emerald-50 via-white to-white">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700">CHITTA</div>
          <nav className="hidden gap-6 text-sm text-slate-600 sm:flex">
            <a href="#problem" className="hover:text-emerald-700">Problem</a>
            <a href="#workflow" className="hover:text-emerald-700">Workflow</a>
            <a href="#methodology" className="hover:text-emerald-700">Methodology</a>
          </nav>
          <Link href="/demo" className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700">
            Launch Demo
          </Link>
        </div>
      </header>

      <main>
        <section className="border-b border-slate-200/80 bg-white/60">
          <div className="mx-auto max-w-5xl px-4 py-16 sm:py-24">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Climate-tech site screening</p>
            <h1 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-5xl">
              AI-assisted wind site screening for terrain-aware renewable energy planning.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
              CHITTA helps teams rapidly evaluate candidate wind turbine locations using real wind and elevation signals,
              structured consultant-style reports, suitability heatmaps, and a transparent audit trail.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/demo" className="rounded-xl bg-emerald-600 px-5 py-3 text-sm font-medium text-white shadow-sm hover:bg-emerald-700">Launch Demo</Link>
              <a href="#demo-sites" className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-medium text-slate-800 shadow-sm hover:bg-slate-50">Try a sample site</a>
            </div>
          </div>
        </section>

        <Section id="problem" title="The problem">
          <p>Early-stage wind development often wastes months on sites that fail basic resource, terrain, or access constraints. Traditional desktop screening is fragmented across wind atlases, elevation tiles, and ad-hoc spreadsheets — with little transparency into how a site score was produced.</p>
          <p className="mt-4">CHITTA compresses that first-pass diligence into a single, auditable workflow so planners can prioritize field studies and engineering spend on the most promising coordinates.</p>
        </Section>

        <Section id="workflow" title="Workflow">
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <WorkflowStep step="01" title="Select a site" body="Search globally or load a curated Indian wind screening location." />
            <WorkflowStep step="02" title="Analyze suitability" body="Fetch NASA POWER wind and OpenTopoData elevation with deterministic scoring." />
            <WorkflowStep step="03" title="Generate heatmap" body="Screen a radius around the site and rank top candidate zones." />
            <WorkflowStep step="04" title="Export & audit" body="Download a consultant PDF and inspect methodology metadata." />
          </div>
        </Section>

        <Section id="data-sources" title="Data sources">
          <ul className="mt-2 list-disc space-y-2 pl-5">
            <li><strong>NASA POWER</strong> — daily WS10M wind time series for mean speed and consistency scoring.</li>
            <li><strong>OpenTopoData (SRTM90m)</strong> — point elevation and nearby sample rings for terrain roughness.</li>
            <li><strong>Mock fallbacks</strong> — deterministic providers when external APIs fail, clearly labeled REAL vs MOCK.</li>
          </ul>
        </Section>

        <Section id="methodology" title="Methodology">
          <p>Scoring formula version <strong>1.0.0</strong> combines wind potential (70% mean speed + 30% consistency), terrain buildability from elevation sample variability, accessibility proxy, and a confidence score based on provider success. Total suitability is a weighted composite: 40% wind, 25% terrain, 20% accessibility, 15% confidence.</p>
          <p className="mt-4">Every analysis returns an <code className="rounded bg-slate-100 px-1">analysisId</code>, methodology metadata, and a step-by-step audit trail for recruiter and stakeholder review.</p>
        </Section>

        <section id="demo-sites" className="border-y border-slate-200/80 bg-emerald-50/40 py-12 sm:py-16">
          <div className="mx-auto max-w-5xl px-4">
            <h2 className="text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">Demo mode — sample wind screening sites</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 sm:text-base">Jump straight into the app with pre-selected locations across India&apos;s wind corridors. Each opens the interactive map, runs site analysis, and supports heatmap generation.</p>
            <div className="mt-6"><SampleSiteButtons linkMode /></div>
          </div>
        </section>

        <Section id="disclaimer" title="Disclaimer">
          <div className="chitta-card rounded-xl bg-slate-50 p-5 text-sm leading-6 text-slate-600">CHITTA is a preliminary screening tool. It is not a bankable wind resource assessment, feasibility study, or engineering recommendation. Results should be validated with on-site measurement, detailed GIS analysis, permitting review, and professional due diligence before any investment or development decision.</div>
        </Section>

        <section className="py-16">
          <div className="mx-auto max-w-5xl px-4 text-center">
            <h2 className="text-2xl font-semibold text-slate-950">Ready to explore a candidate site?</h2>
            <p className="mx-auto mt-3 max-w-xl text-sm text-slate-600">Launch the live demo to analyze coordinates, generate a suitability heatmap, and export a consultant-style PDF.</p>
            <Link href="/demo" className="mt-6 inline-block rounded-xl bg-emerald-600 px-6 py-3 text-sm font-medium text-white shadow-sm hover:bg-emerald-700">Launch Demo</Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 py-8 text-center text-xs text-slate-500">CHITTA — Climate Heuristics &amp; Intelligent Turbine Terrain Analysis</footer>
    </div>
  );
}
