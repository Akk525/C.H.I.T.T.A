"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AgentAnalysisPanel } from "@/components/AgentAnalysisPanel";
import { AIBriefingPanel } from "@/components/AIBriefingPanel";
import { LayoutPanel } from "@/components/LayoutPanel";
import { EconomicsPanel } from "@/components/EconomicsPanel";
import { ConsultantReportView } from "@/components/ConsultantReport";
import { LocationSearch } from "@/components/LocationSearch";
import { MapboxMap } from "@/components/MapboxMap";
import { MethodologyAuditPanel } from "@/components/MethodologyAuditPanel";
import { SampleSiteButtons } from "@/components/SampleSiteButtons";
import { ScoreCard } from "@/components/ScoreCard";
import { TopCandidateZones } from "@/components/TopCandidateZones";
import { exportSiteReport, fetchSiteAnalysis, fetchSiteHeatmap } from "@/lib/api";
import { DEMO_SITES, getDemoSite, type DemoSite } from "@/lib/demoSites";
import type { HeatmapCell, LatLng, SiteAnalysisResponse, SiteHeatmapResponse, TurbinePosition } from "@/lib/types";

const DEFAULT_DEMO = DEMO_SITES[0];
const DEFAULT_CENTER: LatLng = DEFAULT_DEMO.coordinates;

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

  const [turbinePositions, setTurbinePositions] = useState<TurbinePosition[] | null>(null);

  const applySampleSite = useCallback((site: DemoSite) => {
    setPickedLabel(site.label);
    setCenter(site.coordinates);
    setSelected(site.coordinates);
    setActiveSampleId(site.id);
    setHeatmap(null);
    setSelectedHeatmapCell(null);
    setTurbinePositions(null);
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
        .then((res) => setAnalysis(res))
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
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setHeatmapError(msg);
    } finally {
      setHeatmapLoading(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col bg-gradient-to-b from-emerald-50 via-white to-white">
      <header className="border-b border-slate-200 bg-white/70 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Link href="/" className="text-xs text-slate-500 hover:text-emerald-700">← Home</Link>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-800">Demo</span>
            </div>
            <div className="mt-1 text-xs font-semibold tracking-[0.18em] text-emerald-700">
              CHITTA
            </div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-950">
              Climate Heuristics & Intelligent Turbine Terrain Analysis
            </h1>
            <div className="mt-1 text-xs text-slate-600">{title}</div>
          </div>
          <div className="w-full sm:max-w-md">
            <LocationSearch
              token={token}
              onPick={({ label, center }) => {
                setPickedLabel(label);
                setCenter(center);
                setSelected(center);
                setActiveSampleId(null);
                setHeatmap(null);
                setSelectedHeatmapCell(null);
              }}
            />
          </div>
        </div>
      </header>

      <section className="border-b border-slate-200 bg-white/80">
        <div className="mx-auto max-w-6xl px-4 py-3">
          <div className="mb-2 text-xs font-medium text-slate-500">Try sample site</div>
          <SampleSiteButtons
            compact
            activeId={activeSampleId}
            onSelect={applySampleSite}
          />
        </div>
      </section>

      <main className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-12">
        <section className="lg:col-span-7">
          <div className="h-[380px] sm:h-[480px] lg:h-[580px]">
            <MapboxMap
              token={token}
              center={center}
              selected={selected}
              onSelect={(v) => {
                setPickedLabel("Selected point");
                setSelected(v);
                setActiveSampleId(null);
                setHeatmap(null);
                setSelectedHeatmapCell(null);
                setTurbinePositions(null);
              }}
              heatmapCells={heatmap?.cells}
              selectedHeatmapCell={selectedHeatmapCell}
              onHeatmapCellSelect={setSelectedHeatmapCell}
              turbinePositions={turbinePositions ?? undefined}
            />
          </div>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-xs text-slate-600">
              Tip: click anywhere on the map to set the candidate turbine site.
            </div>
            <button
              type="button"
              onClick={handleGenerateHeatmap}
              disabled={heatmapLoading || loading}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {heatmapLoading ? "Generating heatmap…" : "Generate suitability heatmap"}
            </button>
          </div>
          {heatmapError ? (
            <div className="mt-2 text-xs text-rose-700">{heatmapError}</div>
          ) : null}
        </section>

        <section className="lg:col-span-5 flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <ScoreCard
              title="Wind"
              value={formatScore(metrics?.windScore, loading)}
              subtitle={
                metrics?.windSpeedAtHub != null
                  ? `${metrics.windSpeedAtHub.toFixed(1)} m/s at hub • ${providerBadge(sources?.wind?.provider)}`
                  : `Wind potential • ${providerBadge(sources?.wind?.provider)}`
              }
              tone={metrics ? toneForScore(metrics.windScore) : "neutral"}
            />
            <ScoreCard
              title="Terrain"
              value={formatScore(metrics?.terrainScore, loading)}
              subtitle={
                metrics?.elevationM != null
                  ? `${Math.round(metrics.elevationM)}m elev • slope ${metrics.slopePct?.toFixed(1) ?? "?"}%`
                  : `Buildability • ${providerBadge(sources?.elevation?.provider)}`
              }
              tone={metrics ? toneForScore(metrics.terrainScore) : "neutral"}
            />
            <ScoreCard
              title="Infrastructure"
              value={formatScore(metrics?.infrastructureScore, loading)}
              subtitle={
                metrics?.nearestRoadM != null
                  ? `Road ${(metrics.nearestRoadM / 1000).toFixed(1)} km • ${providerBadge(sources?.infrastructure?.provider ?? "osm_overpass")}`
                  : `Road & grid access • ${providerBadge(sources?.infrastructure?.provider ?? "unavailable")}`
              }
              tone={metrics ? toneForScore(metrics.infrastructureScore) : "neutral"}
            />
            <ScoreCard
              title="Environmental"
              value={formatScore(metrics?.environmentalScore, loading)}
              subtitle={
                metrics?.landCoverClass
                  ? `${metrics.landCoverClass} • PA risk: ${metrics.protectedAreaRisk ?? "unknown"}`
                  : `Land cover & protected areas`
              }
              tone={metrics ? toneForScore(metrics.environmentalScore) : "neutral"}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <ScoreCard
              title="Population"
              value={formatScore(metrics?.populationScore, loading)}
              subtitle={
                metrics?.settlementCount15km != null
                  ? `${metrics.settlementCount15km} settlements (15 km)`
                  : "Settlement density proxy"
              }
              tone={metrics ? toneForScore(metrics.populationScore) : "neutral"}
            />
            <ScoreCard
              title="Confidence"
              value={formatScore(metrics?.confidenceScore, loading)}
              subtitle={`Data completeness v2.0`}
              tone={metrics ? toneForScore(metrics.confidenceScore) : "neutral"}
            />
          </div>

          <div className="grid grid-cols-1 gap-3">
            <ScoreCard
              title="Total suitability"
              value={formatScore(total, loading && !analysis)}
              subtitle={
                total != null
                  ? `v2: 35% wind + 20% terrain + 15% infra + 10% env + 10% pop + 10% conf`
                  : metrics
                    ? "Wind or terrain data unavailable"
                    : "Composite heuristic score"
              }
              tone={analysis ? toneForScore(total) : "neutral"}
            />
          </div>

          {heatmap?.bestCells?.length ? (
            <TopCandidateZones
              cells={heatmap.bestCells}
              selected={selectedHeatmapCell}
              onSelect={setSelectedHeatmapCell}
            />
          ) : null}

          {selectedHeatmapCell ? (
            <div className="chitta-card rounded-xl bg-white p-4 text-sm text-slate-700 shadow-sm">
              <div className="font-semibold text-slate-900">Selected zone</div>
              <div className="mt-1">{selectedHeatmapCell.label}</div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                <div>Total: {formatScore(selectedHeatmapCell.metrics.totalSuitability)}</div>
                <div>Wind: {formatMetric(selectedHeatmapCell.metrics.windScore)} ({selectedHeatmapCell.providerStatus.wind})</div>
                <div>Terrain: {formatMetric(selectedHeatmapCell.metrics.terrainScore)} ({selectedHeatmapCell.providerStatus.elevation})</div>
                <div>Access: {formatScore(selectedHeatmapCell.metrics.accessibilityScore)}</div>
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="chitta-card rounded-xl bg-rose-50 p-4 text-sm text-rose-900">
              <div className="font-semibold">Analysis request failed</div>
              <div className="mt-1 text-rose-800">{error}</div>
            </div>
          ) : null}

          {analysis ? (
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={handleExportReport}
                disabled={exportLoading || loading}
                className="rounded-xl border border-emerald-200 bg-white px-4 py-2 text-sm font-medium text-emerald-800 shadow-sm transition-colors hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {exportLoading ? "Exporting PDF…" : "Export Site Assessment"}
              </button>
              {exportError ? (
                <div className="text-xs text-rose-700">{exportError}</div>
              ) : null}
            </div>
          ) : null}

          {analysis?.economicMetrics ? (
            <div className="mt-1">
              <EconomicsPanel
                metrics={analysis.economicMetrics}
                windSpeedAtHub={metrics?.windSpeedAtHub ?? null}
                terrainScore={metrics?.terrainScore ?? null}
                infraScore={metrics?.infrastructureScore ?? null}
              />
            </div>
          ) : null}

          {analysis?.agentAnalysis ? (
            <div className="mt-1">
              <AgentAnalysisPanel agentAnalysis={analysis.agentAnalysis} />
            </div>
          ) : null}

          {analysis ? (
            <div className="mt-1">
              <LayoutPanel
                latitude={selected.latitude}
                longitude={selected.longitude}
                onLayoutResult={(positions) => setTurbinePositions(positions)}
              />
            </div>
          ) : null}

          {analysis ? (
            <div className="mt-1">
              <AIBriefingPanel
                mode="site"
                siteAnalysis={analysis}
              />
            </div>
          ) : null}

          {analysis ? (
            <div className="mt-1">
              <div className="mb-2 text-xs font-semibold tracking-[0.14em] text-slate-500">
                CONSULTANT REPORT
              </div>
              <ConsultantReportView report={analysis.report} />
              <div className="mt-3">
                <MethodologyAuditPanel
                  analysisId={analysis.analysisId}
                  methodology={analysis.methodology}
                  auditTrail={analysis.auditTrail}
                  heatmapAuditTrail={heatmap?.auditTrail}
                />
              </div>
            </div>
          ) : (
            <div className="chitta-card rounded-xl bg-white p-4 text-sm text-slate-700">
              {loading ? "Analyzing site…" : "Pick a site to generate a report."}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
