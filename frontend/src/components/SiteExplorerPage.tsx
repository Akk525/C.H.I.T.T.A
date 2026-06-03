"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AgentAnalysisPanel } from "@/components/AgentAnalysisPanel";
import { AIBriefingPanel } from "@/components/AIBriefingPanel";
import { DevelopmentSignalsPanel } from "@/components/DevelopmentSignalsPanel";
import { LayoutPanel } from "@/components/LayoutPanel";
import { EconomicsPanel } from "@/components/EconomicsPanel";
import { ConsultantReportView } from "@/components/ConsultantReport";
import { LocationSearch } from "@/components/LocationSearch";
import { MapboxMap } from "@/components/MapboxMap";
import { LoadingProgress } from "@/components/LoadingProgress";
import { MethodologyAuditPanel } from "@/components/MethodologyAuditPanel";
import { SampleSiteButtons } from "@/components/SampleSiteButtons";
import { ScoreCard } from "@/components/ScoreCard";
import { TopCandidateZones } from "@/components/TopCandidateZones";
import { AppShell } from "@/components/ui/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { exportSiteReport, fetchSiteAnalysis, fetchSiteHeatmap, saveToHistory } from "@/lib/api";
import { DEMO_SITES, getDemoSite, type DemoSite } from "@/lib/demoSites";
import type { HeatmapCell, LatLng, SiteAnalysisResponse, SiteHeatmapResponse, TurbinePosition } from "@/lib/types";

const DEFAULT_DEMO = DEMO_SITES[0];
const DEFAULT_CENTER: LatLng = DEFAULT_DEMO.coordinates;

type ResultsTab = "overview" | "agents" | "report" | "tools" | "ai";

const RESULT_TABS: { id: ResultsTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "agents", label: "Agents" },
  { id: "report", label: "Report" },
  { id: "tools", label: "Tools" },
  { id: "ai", label: "AI Briefing" },
];

function clampScore(v: number | null | undefined) {
  if (v == null) return null;
  return Math.max(0, Math.min(100, Math.round(v)));
}

function formatMetric(v: number | null | undefined) {
  if (v == null) return "Unavailable";
  return `${clampScore(v)}`;
}

function formatScore(v: number | null | undefined, loading = false) {
  if (loading) return "…";
  if (v == null) return "Unavailable";
  return `${formatMetric(v)}/100`;
}

function toneForScore(v: number | null | undefined): "neutral" | "good" | "warn" {
  if (v == null) return "neutral";
  if (v >= 75) return "good";
  if (v < 45) return "warn";
  return "neutral";
}

function providerBadge(v: unknown) {
  if (typeof v !== "string") return "—";
  if (v === "unavailable") return "UNAVAILABLE";
  if (v === "mock") return "MOCK";
  return "REAL";
}

type DebugSources = {
  wind?: { provider?: string };
  elevation?: { provider?: string };
  infrastructure?: { provider?: string };
};

export default function SiteExplorerPage() {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim() || null;
  const searchParams = useSearchParams();

  const [center, setCenter] = useState<LatLng>(DEFAULT_CENTER);
  const [selected, setSelected] = useState<LatLng>(DEFAULT_CENTER);
  const [pickedLabel, setPickedLabel] = useState<string>(DEFAULT_DEMO.label);
  const [activeSampleId, setActiveSampleId] = useState<string | null>(DEFAULT_DEMO.id);
  const [resultsTab, setResultsTab] = useState<ResultsTab>("overview");

  const [analysis, setAnalysis] = useState<SiteAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const [heatmap, setHeatmap] = useState<SiteHeatmapResponse | null>(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [selectedHeatmapCell, setSelectedHeatmapCell] = useState<HeatmapCell | null>(null);
  const heatmapAbortRef = useRef<AbortController | null>(null);

  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const exportAbortRef = useRef<AbortController | null>(null);

  const [saveLoading, setSaveLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");

  const [turbinePositions, setTurbinePositions] = useState<TurbinePosition[] | null>(null);

  const applySampleSite = useCallback((site: DemoSite) => {
    setPickedLabel(site.label);
    setCenter(site.coordinates);
    setSelected(site.coordinates);
    setActiveSampleId(site.id);
    setHeatmap(null);
    setSelectedHeatmapCell(null);
    setTurbinePositions(null);
    setResultsTab("overview");
  }, []);

  const resetSiteContext = useCallback(() => {
    setHeatmap(null);
    setSelectedHeatmapCell(null);
    setTurbinePositions(null);
    setResultsTab("overview");
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const sampleId = searchParams.get("sample");
      if (!sampleId) return;
      const site = getDemoSite(sampleId);
      if (site) applySampleSite(site);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [searchParams, applySampleSite]);

  const title = useMemo(() => {
    const lat = selected.latitude.toFixed(4);
    const lng = selected.longitude.toFixed(4);
    return `${pickedLabel} · ${lat}, ${lng}`;
  }, [pickedLabel, selected.latitude, selected.longitude]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setError(null);
      setLoading(true);
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      fetchSiteAnalysis(selected, abortRef.current.signal)
        .then((res) => {
          setAnalysis(res);
          setResultsTab("overview");
        })
        .catch((e: unknown) => {
          const msg = e instanceof Error ? e.message : "Unknown error";
          setError(msg);
        })
        .finally(() => setLoading(false));
    }, 0);

    return () => {
      window.clearTimeout(handle);
      abortRef.current?.abort();
    };
  }, [selected]);

  const metrics = analysis?.metrics;
  const total = analysis?.totalSuitabilityScore ?? null;
  const sources = (analysis?.debug as { sources?: DebugSources } | undefined)?.sources;
  const coordinatorDecision = analysis?.agentAnalysis?.coordinator?.finalDecision;
  const showResultsPanel = loading || !!analysis || !!error;

  async function handleSaveToHistory() {
    if (!analysis) return;
    setSaveLoading(true);
    setSaveStatus("idle");
    try {
      await saveToHistory({
        runType: "site",
        label: `${pickedLabel} · ${selected.latitude.toFixed(4)}, ${selected.longitude.toFixed(4)}`,
        payload: analysis as unknown as Record<string, unknown>,
      });
      setSaveStatus("saved");
    } catch {
      setSaveStatus("error");
    } finally {
      setSaveLoading(false);
    }
  }

  async function handleExportReport() {
    if (!analysis) return;
    setExportError(null);
    setExportLoading(true);
    exportAbortRef.current?.abort();
    exportAbortRef.current = new AbortController();

    try {
      const blob = await exportSiteReport(
        { analysis, heatmap: heatmap ?? null },
        exportAbortRef.current.signal,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "chitta-site-assessment.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setExportError(msg);
    } finally {
      setExportLoading(false);
    }
  }

  async function handleGenerateHeatmap() {
    setHeatmapError(null);
    setHeatmapLoading(true);
    heatmapAbortRef.current?.abort();
    heatmapAbortRef.current = new AbortController();

    try {
      const res = await fetchSiteHeatmap(
        {
          latitude: selected.latitude,
          longitude: selected.longitude,
          radiusKm: 10,
          gridSize: 5,
        },
        heatmapAbortRef.current.signal,
      );
      setHeatmap(res);
      setSelectedHeatmapCell(res.bestCells[0] ?? null);
      setResultsTab("tools");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setHeatmapError(msg);
    } finally {
      setHeatmapLoading(false);
    }
  }

  return (
    <AppShell
      header={
        <div className="space-y-4">
          <PageHeader
            eyebrow="Site analysis"
            title="Site Explorer"
            subtitle={title}
          />
          <div className="max-w-md">
            <LocationSearch
              token={token}
              onPick={({ label, center: pickedCenter }) => {
                setPickedLabel(label);
                setCenter(pickedCenter);
                setSelected(pickedCenter);
                setActiveSampleId(null);
                resetSiteContext();
              }}
            />
          </div>
          <SampleSiteButtons compact activeId={activeSampleId} onSelect={applySampleSite} />
        </div>
      }
    >
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-4 py-4">
        {/* Map + scores workspace — fixed footprint, does not grow with reports */}
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
          <section className="space-y-3 lg:col-span-7 lg:sticky lg:top-36 lg:z-10">
            <div className="chitta-panel overflow-hidden">
              <div className="h-[min(48vh,440px)] min-h-[280px] w-full">
                <MapboxMap
                  token={token}
                  center={center}
                  selected={selected}
                  onSelect={(v) => {
                    setPickedLabel("Selected point");
                    setSelected(v);
                    setActiveSampleId(null);
                    resetSiteContext();
                  }}
                  heatmapCells={heatmap?.cells}
                  selectedHeatmapCell={selectedHeatmapCell}
                  onHeatmapCellSelect={setSelectedHeatmapCell}
                  turbinePositions={turbinePositions ?? undefined}
                />
              </div>
              <div className="flex flex-col gap-2 border-t border-[var(--chitta-border)] bg-[var(--chitta-bg)] px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-[11px] text-[var(--chitta-muted)]">
                  Click the map to move the candidate site.
                </p>
                <Button
                  type="button"
                  onClick={handleGenerateHeatmap}
                  disabled={heatmapLoading || loading}
                  className="!px-3 !py-1.5 !text-xs"
                >
                  {heatmapLoading ? "Generating…" : "Suitability heatmap"}
                </Button>
              </div>
            </div>
            {heatmapLoading ? <LoadingProgress variant="heatmap" compact /> : null}
            {heatmapError ? (
              <p className="text-xs text-rose-700">{heatmapError}</p>
            ) : null}
          </section>

          <aside className="flex flex-col gap-3 lg:col-span-5">
            {loading ? (
              <LoadingProgress
                variant="site-analysis"
                detail={`${pickedLabel} · ${selected.latitude.toFixed(4)}, ${selected.longitude.toFixed(4)}`}
              />
            ) : null}

            {error ? (
              <div className="chitta-panel rounded-xl bg-rose-50 p-3 text-sm text-rose-900">
                <div className="font-semibold">Analysis failed</div>
                <p className="mt-1 text-rose-800">{error}</p>
              </div>
            ) : null}

            <div
              className={`chitta-panel p-3 ${loading ? "chitta-score-skeleton opacity-90" : ""}`}
            >
              <div className="mb-2 flex items-end justify-between gap-2">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--chitta-muted)]">
                    Suitability
                  </p>
                  <p className="chitta-mono text-3xl font-bold tracking-tight text-[var(--chitta-ink)]">
                    {formatScore(total, loading && !analysis)}
                  </p>
                </div>
                {coordinatorDecision ? (
                  <Badge tone="success">{coordinatorDecision}</Badge>
                ) : null}
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <ScoreCard
                  title="Wind"
                  loading={loading}
                  value={formatScore(metrics?.windScore, loading)}
                  subtitle={
                    metrics?.windSpeedAtHub != null
                      ? `${metrics.windSpeedAtHub.toFixed(1)} m/s`
                      : providerBadge(sources?.wind?.provider)
                  }
                  tone={metrics ? toneForScore(metrics.windScore) : "neutral"}
                />
                <ScoreCard
                  title="Terrain"
                  loading={loading}
                  value={formatScore(metrics?.terrainScore, loading)}
                  subtitle={
                    metrics?.elevationM != null
                      ? `${Math.round(metrics.elevationM)} m`
                      : providerBadge(sources?.elevation?.provider)
                  }
                  tone={metrics ? toneForScore(metrics.terrainScore) : "neutral"}
                />
                <ScoreCard
                  title="Infra"
                  loading={loading}
                  value={formatScore(metrics?.infrastructureScore, loading)}
                  subtitle={
                    metrics?.nearestRoadM != null
                      ? `${(metrics.nearestRoadM / 1000).toFixed(1)} km road`
                      : "Access"
                  }
                  tone={metrics ? toneForScore(metrics.infrastructureScore) : "neutral"}
                />
                <ScoreCard
                  title="Env"
                  loading={loading}
                  value={formatScore(metrics?.environmentalScore, loading)}
                  subtitle={metrics?.landCoverClass ?? "Land cover"}
                  tone={metrics ? toneForScore(metrics.environmentalScore) : "neutral"}
                />
                <ScoreCard
                  title="Pop"
                  loading={loading}
                  value={formatScore(metrics?.populationScore, loading)}
                  subtitle={
                    metrics?.settlementCount15km != null
                      ? `${metrics.settlementCount15km} settlements`
                      : "Social"
                  }
                  tone={metrics ? toneForScore(metrics.populationScore) : "neutral"}
                />
                <ScoreCard
                  title="Conf"
                  loading={loading}
                  value={formatScore(metrics?.confidenceScore, loading)}
                  subtitle="Data quality"
                  tone={metrics ? toneForScore(metrics.confidenceScore) : "neutral"}
                />
              </div>
            </div>

            {analysis ? (
              <div className="chitta-panel flex flex-col gap-2 p-3">
                <div className="flex gap-2">
                  <Button
                    type="button"
                    onClick={handleExportReport}
                    disabled={exportLoading || loading}
                    className="flex-1 !py-2 !text-xs"
                  >
                    {exportLoading ? "Exporting…" : "Export PDF"}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleSaveToHistory}
                    disabled={saveLoading}
                    className="!py-2 !text-xs"
                  >
                    {saveLoading ? "…" : saveStatus === "saved" ? "Saved" : "Save"}
                  </Button>
                </div>
                {exportLoading ? <LoadingProgress variant="export-pdf" compact /> : null}
                {exportError ? <p className="text-xs text-rose-700">{exportError}</p> : null}
                {saveStatus === "error" ? (
                  <p className="text-xs text-rose-700">Save failed — is PostgreSQL running?</p>
                ) : null}
              </div>
            ) : !loading ? (
              <p className="text-center text-xs text-[var(--chitta-muted)]">
                Select a site to unlock reports and tools below.
              </p>
            ) : null}
          </aside>
        </div>

        {/* Tabbed results — scroll contained, page height stays bounded */}
        {showResultsPanel ? (
          <section className="chitta-panel flex min-h-[280px] max-h-[min(72vh,780px)] flex-col overflow-hidden">
            <div className="flex shrink-0 items-center justify-between gap-2 border-b border-[var(--chitta-border)] bg-[var(--chitta-bg)] px-2 py-2">
              <div
                className="flex gap-1 overflow-x-auto"
                role="tablist"
                aria-label="Site analysis sections"
              >
                {RESULT_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    aria-selected={resultsTab === tab.id}
                    disabled={!analysis && tab.id !== "overview"}
                    onClick={() => setResultsTab(tab.id)}
                    className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      resultsTab === tab.id
                        ? "bg-[var(--chitta-surface)] text-[var(--chitta-accent)] shadow-sm ring-1 ring-[var(--chitta-border)]"
                        : "text-[var(--chitta-muted)] hover:bg-[var(--chitta-surface)]/70 disabled:opacity-40"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              {analysis ? (
                <span className="hidden shrink-0 text-[10px] text-slate-400 sm:inline">
                  Scroll inside panel ↓
                </span>
              ) : null}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {loading && !analysis ? (
                <p className="text-sm text-slate-500">Analysis in progress…</p>
              ) : null}

              {error && !analysis ? (
                <p className="text-sm text-rose-700">{error}</p>
              ) : null}

              {!loading && !analysis && !error ? (
                <p className="text-sm text-slate-500">
                  Pick a site on the map to generate reports.
                </p>
              ) : null}

              {resultsTab === "overview" && analysis ? (
                <div className="space-y-4">
                  {analysis.economicMetrics ? (
                    <EconomicsPanel
                      metrics={analysis.economicMetrics}
                      windSpeedAtHub={metrics?.windSpeedAtHub ?? null}
                      terrainScore={metrics?.terrainScore ?? null}
                      infraScore={metrics?.infrastructureScore ?? null}
                    />
                  ) : (
                    <p className="text-sm text-slate-500">No economic metrics for this run.</p>
                  )}
                </div>
              ) : null}

              {resultsTab === "agents" && analysis?.agentAnalysis ? (
                <AgentAnalysisPanel agentAnalysis={analysis.agentAnalysis} />
              ) : null}

              {resultsTab === "agents" && analysis && !analysis.agentAnalysis ? (
                <p className="text-sm text-slate-500">No agent analysis available.</p>
              ) : null}

              {resultsTab === "report" && analysis ? (
                <div className="space-y-4">
                  <ConsultantReportView report={analysis.report} />
                  <MethodologyAuditPanel
                    analysisId={analysis.analysisId}
                    methodology={analysis.methodology}
                    auditTrail={analysis.auditTrail}
                    heatmapAuditTrail={heatmap?.auditTrail}
                  />
                </div>
              ) : null}

              {resultsTab === "tools" && analysis ? (
                <div className="space-y-4">
                  {heatmap?.bestCells?.length ? (
                    <TopCandidateZones
                      cells={heatmap.bestCells}
                      selected={selectedHeatmapCell}
                      onSelect={setSelectedHeatmapCell}
                    />
                  ) : (
                    <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/80 px-3 py-4 text-center text-xs text-slate-500">
                      Generate a suitability heatmap from the map panel to see top zones here.
                    </p>
                  )}
                  {selectedHeatmapCell ? (
                    <div className="chitta-card rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                      <div className="font-semibold text-slate-900">Selected zone</div>
                      <div className="mt-1">{selectedHeatmapCell.label}</div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          Total: {formatScore(selectedHeatmapCell.metrics.totalSuitability)}
                        </div>
                        <div>
                          Wind: {formatMetric(selectedHeatmapCell.metrics.windScore)} (
                          {selectedHeatmapCell.providerStatus.wind})
                        </div>
                        <div>
                          Terrain: {formatMetric(selectedHeatmapCell.metrics.terrainScore)} (
                          {selectedHeatmapCell.providerStatus.elevation})
                        </div>
                        <div>
                          Access: {formatScore(selectedHeatmapCell.metrics.accessibilityScore)}
                        </div>
                      </div>
                    </div>
                  ) : null}
                  <LayoutPanel
                    latitude={selected.latitude}
                    longitude={selected.longitude}
                    onLayoutResult={(positions) => setTurbinePositions(positions)}
                  />
                  <DevelopmentSignalsPanel
                    regionName={pickedLabel}
                    latitude={selected.latitude}
                    longitude={selected.longitude}
                    radiusKm={50}
                  />
                </div>
              ) : null}

              {resultsTab === "ai" && analysis ? (
                <AIBriefingPanel mode="site" siteAnalysis={analysis} />
              ) : null}
            </div>
          </section>
        ) : null}
      </main>
    </AppShell>
  );
}
