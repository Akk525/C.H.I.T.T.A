"use client";

import type { ConsultantReport } from "@/lib/types";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="chitta-card rounded-xl bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold tracking-wide text-slate-900">
        {title}
      </h3>
      <div className="mt-2 text-sm leading-6 text-slate-700">{children}</div>
    </section>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc pl-5 space-y-1">
      {items.map((t, i) => (
        <li key={`${i}-${t.slice(0, 16)}`}>{t}</li>
      ))}
    </ul>
  );
}

export function ConsultantReportView({ report }: { report: ConsultantReport }) {
  return (
    <div className="grid gap-3">
      <Section title="Executive Summary">{report.executiveSummary}</Section>
      <Section title="Site Strengths">
        <Bullets items={report.siteStrengths} />
      </Section>
      <Section title="Risks">
        <Bullets items={report.risks} />
      </Section>
      <Section title="Recommendations">
        <Bullets items={report.recommendations} />
      </Section>
      <Section title="Data Sources">
        <Bullets items={report.dataSources ?? []} />
      </Section>
      <Section title="Confidence Notes">
        <Bullets items={report.confidenceNotes} />
      </Section>
    </div>
  );
}

