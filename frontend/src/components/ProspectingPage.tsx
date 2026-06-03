"use client";

import { useRef, useState } from "react";
import { AIBriefingPanel } from "@/components/AIBriefingPanel";
import { LoadingProgress } from "@/components/LoadingProgress";
import { AppShell } from "@/components/ui/AppShell";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { DevelopmentSignalsPanel } from "@/components/DevelopmentSignalsPanel";
import { ProspectingCandidatePanel } from "@/components/ProspectingCandidatePanel";
import { ProspectingClusterCard } from "@/components/ProspectingClusterCard";
import { ProspectingMap } from "@/components/ProspectingMap";
import { SimulationPanel } from "@/components/SimulationPanel";
import { exportProspectingReport, runProspecting, saveToHistory } from "@/lib/api";
import type {
  LatLng,
  ProspectingCandidate,
  ProspectingCluster,
  ProspectingResponse,
  SimulationResponse,
  SynthesisResponse,
} from "@/lib/types";

// ── Sample regions ────────────────────────────────────────────────────────────
const SAMPLE_REGIONS = [
  {
    id: "karnataka",
    label: "Karnataka Wind Corridor",
    centerLatitude: 14.5,
    centerLongitude: 76.4,
    radiusKm: 75,
    gridSize: 5,
  },
  {
    id: "kutch",
    label: "Kutch Wind Belt",
    centerLatitude: 23.5,
    centerLongitude: 70.0,
    radiusKm: 80,
    gridSize: 5,
  },
  {
    id: "tirunelveli",
    label: "Tirunelveli Corridor",
    centerLatitude: 8.7,
    centerLongitude: 77.5,
    radiusKm: 60,
    gridSize: 5,
  },
] as const;

const GRID_OPTIONS = [3, 4, 5, 6, 7] as const;

// ── Helpers ───────────────────────────────────────────────────────────────────
function scoreColour(v: number | null): string {
  if (v === null) return "text-slate-400";
  if (v >= 70) return "text-emerald-700";
  if (v >= 55) return "text-blue-700";
  if (v >= 40) return "text-amber-700";
  return "text-rose-700";
}

function decisionBadge(d: string | null): React.ReactNode {
  if (!d) return null;
  const cls: Record<string, string> = {
    promising: "bg-emerald-100 text-emerald-800",
    mixed:     "bg-blue-100 text-blue-800",
    caution:   "bg-amber-100 text-amber-800",
    poor:      "bg-rose-100 text-rose-800",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${cls[d] ?? "bg-slate-100 text-slate-600"}`}>
      {d}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function ProspectingPage() {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim() || null;

  const [regionName, setRegionName] = useState("Karnataka Wind Corridor");
  const [centerLat, setCenterLat] = useState(14.5);
  const [centerLng, setCenterLng] = useState(76.4);
  const [radiusKm, setRadiusKm] = useState(75);
  const [gridSize, setGridSize] = useState<number>(5);

  const [result, setResult] = useState<ProspectingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<ProspectingCandidate | null>(null);
  const [simOpen, setSimOpen] = useState(false);
  const [simResult, setSimResult] = useState<SimulationResponse | null>(null);
  const [synthesisResult, setSynthesisResult] = useState<SynthesisResponse | null>(null);
  const [aiBriefingMode, setAiBriefingMode] = useState<"site" | "prospecting" | "simulation" | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");
  const abortRef = useRef<AbortController | null>(null);
  const exportAbortRef = useRef<AbortController | null>(null);

  const mapCenter: LatLng = { latitude: centerLat, longitude: centerLng };
  const candidateCount = gridSize * gridSize;

  function applyPreset(region: (typeof SAMPLE_REGIONS)[number]) {
    setRegionName(region.label);
    setCenterLat(region.centerLatitude);
    setCenterLng(region.centerLongitude);
    setRadiusKm(region.radiusKm);
    setGridSize(region.gridSize);
    setResult(null);
    setSelectedCandidate(null);
    setError(null);
  }

  async function handleRun() {
    setError(null);
    setLoading(true);
    setResult(null);
    setSelectedCandidate(null);
    setSimResult(null);
    setSynthesisResult(null);
    setAiBriefingMode(null);
    setExportError(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await runProspecting(
        {
          regionName,
          centerLatitude: centerLat,
          centerLongitude: centerLng,
          radiusKm,
          gridSize,
          maxCandidates: candidateCount,
        },
        abortRef.current.signal,
      );
      setResult(res);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      setError((e instanceof Error ? e.message : "Unknown error") ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function handleFocusCluster(cluster: ProspectingCluster) {
    if (!result) return;
    const nearest = result.candidates
      .filter((c) => c.totalSuitability !== null)
      .sort((a, b) => {
        const da = Math.hypot(a.latitude - cluster.centroidLatitude, a.longitude - cluster.centroidLongitude);
        const db = Math.hypot(b.latitude - cluster.centroidLatitude, b.longitude - cluster.centroidLongitude);
        return da - db;
      })[0];
    if (nearest) setSelectedCandidate(nearest);
  }

  async function handleSaveToHistory() {
    if (!result) return;
    setSaveLoading(true);
    setSaveStatus("idle");
    try {
      await saveToHistory({
        runType: "prospecting",
        label: `${regionName} · ${result.generatedAt.slice(0, 10)}`,
        payload: result as unknown as Record<string, unknown>,
      });
      setSaveStatus("saved");
    } catch {
      setSaveStatus("error");
    } finally {
      setSaveLoading(false);
    }
  }

  async function handleExportReport() {
    if (!result) return;
    setExportError(null);
    setExportLoading(true);
    exportAbortRef.current?.abort();
    exportAbortRef.current = new AbortController();

    try {
      const blob = await exportProspectingReport(
        {
          prospecting: result,
          simulation: simResult ?? null,
          synthesis: synthesisResult ?? null,
        },
        exportAbortRef.current.signal,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "chitta-prospecting-report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      setExportError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExportLoading(false);
    }
  }

  return (
    <AppShell
      header={
        <PageHeader
          eyebrow="Regional screening"
          title="Wind Prospecting"
          subtitle="Screen candidate sites across a region and surface high-potential wind corridors."
        />
      }
    >
      <main className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-12">
        {/* Config panel */}
        <aside className="lg:col-span-3 space-y-4">
          <div className="chitta-panel space-y-3 p-4">
            <SectionLabel>Region presets</SectionLabel>
            <div className="space-y-2">
              {SAMPLE_REGIONS.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => applyPreset(r)}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition-colors ${
                    regionName === r.label
                      ? "border-[var(--chitta-accent)] bg-[var(--chitta-accent-soft)] text-[var(--chitta-ink)]"
                      : "border-[var(--chitta-border)] text-[var(--chitta-ink)] hover:bg-[var(--chitta-bg)]"
                  }`}
                >
                  <div className="font-medium">{r.label}</div>
                  <div className="text-slate-400">{r.centerLatitude}°N, {r.centerLongitude}°E · {r.radiusKm}km</div>
                </button>
              ))}
            </div>
          </div>

          <div className="chitta-panel space-y-4 p-4">
            <SectionLabel>Configuration</SectionLabel>

            <div>
              <label className="text-xs text-slate-600 block mb-1">Region name</label>
              <input
                type="text"
                value={regionName}
                onChange={(e) => setRegionName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-300"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-slate-600 block mb-1">Centre lat</label>
                <input
                  type="number"
                  step="0.01"
                  value={centerLat}
                  onChange={(e) => setCenterLat(parseFloat(e.target.value) || 0)}
                  className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-300"
                />
              </div>
              <div>
                <label className="text-xs text-slate-600 block mb-1">Centre lng</label>
                <input
                  type="number"
                  step="0.01"
                  value={centerLng}
                  onChange={(e) => setCenterLng(parseFloat(e.target.value) || 0)}
                  className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-300"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-600 block mb-1">
                Radius: <span className="font-semibold text-slate-800">{radiusKm} km</span>
              </label>
              <input
                type="range"
                min={20}
                max={200}
                step={5}
                value={radiusKm}
                onChange={(e) => setRadiusKm(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>20 km</span><span>200 km</span>
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-600 block mb-1">Grid size</label>
              <div className="flex gap-1">
                {GRID_OPTIONS.map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGridSize(g)}
                    className={`flex-1 rounded-lg border py-1.5 text-xs font-medium transition-colors ${
                      gridSize === g
                        ? "border-[var(--chitta-accent)] bg-[var(--chitta-accent-soft)] text-[var(--chitta-accent)]"
                        : "border-[var(--chitta-border)] text-[var(--chitta-muted)] hover:bg-[var(--chitta-bg)]"
                    }`}
                  >
                    {g}×{g}
                  </button>
                ))}
              </div>
              <div className="mt-1 text-[10px] text-slate-400">{candidateCount} candidate points</div>
            </div>

            <Button
              type="button"
              onClick={handleRun}
              disabled={loading}
              className="w-full"
            >
              {loading
                ? `Screening ${candidateCount} sites…`
                : "Run Prospecting"}
            </Button>

            {error && (
              <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800">{error}</div>
            )}
          </div>

          {/* Methodology summary + export */}
          {result && (
            <div className="chitta-panel space-y-2 p-4">
              <SectionLabel>Run summary</SectionLabel>
              <div className="text-xs text-slate-600 space-y-1">
                <div><span className="font-medium">{result.candidateCount}</span> candidates screened</div>
                <div><span className="font-medium">{result.enrichedCount}</span> fully enriched</div>
                <div><span className="font-medium">{result.clusters.length}</span> zones identified</div>
                <div className="text-slate-400">{result.generatedAt}</div>
              </div>
              <div className="text-[10px] text-slate-400 border-t border-slate-100 pt-2">
                {result.auditTrail.map((line, i) => <div key={i}>{line}</div>)}
              </div>
              <div className="border-t border-slate-100 pt-3 space-y-2">
                <button
                  type="button"
                  onClick={handleExportReport}
                  disabled={exportLoading || loading}
                  className="w-full rounded-xl border border-emerald-200 bg-white px-4 py-2 text-sm font-medium text-emerald-800 shadow-sm transition-colors hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {exportLoading ? "Exporting PDF…" : "Export Prospecting Report"}
                </button>
                <button
                  type="button"
                  onClick={handleSaveToHistory}
                  disabled={saveLoading}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 disabled:opacity-60"
                >
                  {saveLoading ? "Saving…" : saveStatus === "saved" ? "✓ Saved to History" : "Save to History"}
                </button>
                {saveStatus === "error" && (
                  <div className="text-[10px] text-rose-700">Save failed — is the database running?</div>
                )}
                {(simResult || synthesisResult) && (
                  <div className="text-[10px] text-slate-400 space-y-0.5">
                    {simResult && <div>Includes simulation findings</div>}
                    {synthesisResult && <div>Includes AI synthesis</div>}
                  </div>
                )}
                {exportError && (
                  <div className="text-xs text-rose-700">{exportError}</div>
                )}
              </div>
            </div>
          )}
        </aside>

        {/* Map + results */}
        <div className="lg:col-span-9 space-y-4">
          {/* Map */}
          <div className="h-[440px] sm:h-[520px]">
            <ProspectingMap
              token={token}
              center={mapCenter}
              candidates={result?.candidates ?? []}
              selectedId={selectedCandidate?.id ?? null}
              onSelect={setSelectedCandidate}
            />
          </div>

          {/* Candidate detail panel */}
          {selectedCandidate && (
            <ProspectingCandidatePanel
              candidate={selectedCandidate}
              onClose={() => setSelectedCandidate(null)}
            />
          )}

          {/* Cluster cards */}
          {result && result.clusters.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-semibold tracking-[0.12em] text-slate-500">
                IDENTIFIED ZONES
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {result.clusters.map((cl) => (
                  <ProspectingClusterCard
                    key={cl.id}
                    cluster={cl}
                    onFocus={handleFocusCluster}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Top candidates table */}
          {result && result.topCandidates.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-semibold tracking-[0.12em] text-slate-500">
                TOP CANDIDATES (fully enriched)
              </div>
              <div className="chitta-card overflow-hidden rounded-xl bg-white shadow-sm">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50 text-left text-[11px] text-slate-500">
                      <th className="px-3 py-2.5 font-medium">Rank</th>
                      <th className="px-3 py-2.5 font-medium">Score</th>
                      <th className="px-3 py-2.5 font-medium">Decision</th>
                      <th className="px-3 py-2.5 font-medium">Wind</th>
                      <th className="px-3 py-2.5 font-medium">Terrain</th>
                      <th className="px-3 py-2.5 font-medium">CF</th>
                      <th className="px-3 py-2.5 font-medium">LCOE</th>
                      <th className="px-3 py-2.5 font-medium">Payback</th>
                      <th className="px-3 py-2.5 font-medium">Coordinates</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.topCandidates.map((c, i) => (
                      <tr
                        key={c.id}
                        onClick={() => setSelectedCandidate(c)}
                        className={`border-b border-slate-50 cursor-pointer transition-colors hover:bg-slate-50 ${
                          selectedCandidate?.id === c.id ? "bg-emerald-50" : ""
                        }`}
                      >
                        <td className="px-3 py-2 text-slate-400">#{i + 1}</td>
                        <td className={`px-3 py-2 font-semibold ${scoreColour(c.totalSuitability)}`}>
                          {c.totalSuitability?.toFixed(0) ?? "–"}
                        </td>
                        <td className="px-3 py-2">{decisionBadge(c.finalDecision)}</td>
                        <td className="px-3 py-2 text-slate-600">{c.windScore?.toFixed(0) ?? "–"}</td>
                        <td className="px-3 py-2 text-slate-600">{c.terrainScore?.toFixed(0) ?? "–"}</td>
                        <td className="px-3 py-2 text-slate-600">
                          {c.capacityFactor != null ? `${(c.capacityFactor * 100).toFixed(0)}%` : "–"}
                        </td>
                        <td className="px-3 py-2 text-slate-600">
                          {c.lcoeUsdPerMwh != null ? `$${c.lcoeUsdPerMwh.toFixed(0)}` : "–"}
                        </td>
                        <td className="px-3 py-2 text-slate-600">
                          {c.paybackYears != null ? `${c.paybackYears.toFixed(0)}yr` : "–"}
                        </td>
                        <td className="px-3 py-2 text-slate-400">
                          {c.latitude.toFixed(3)}, {c.longitude.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Scenario Simulation */}
          {result && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <div className="text-xs font-semibold tracking-[0.12em] text-slate-500">
                  SCENARIO SIMULATION
                </div>
                <button
                  type="button"
                  onClick={() => setSimOpen((v) => !v)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    simOpen
                      ? "bg-blue-100 text-blue-800 hover:bg-blue-200"
                      : "border border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {simOpen ? "Close Simulation" : "Simulate Scenarios"}
                </button>
              </div>
              {simOpen && (
                <SimulationPanel
                  candidates={result.candidates}
                  onClose={() => setSimOpen(false)}
                  onResult={(res) => {
                    setSimResult(res);
                    setAiBriefingMode("simulation");
                  }}
                />
              )}
            </div>
          )}

          {/* Development Signals */}
          {result && (
            <div>
              <DevelopmentSignalsPanel
                regionName={result.region?.name ?? regionName}
                latitude={centerLat}
                longitude={centerLng}
                radiusKm={radiusKm}
              />
            </div>
          )}

          {/* AI Briefing */}
          {result && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <div className="text-xs font-semibold tracking-[0.12em] text-slate-500">
                  AI BRIEFING
                </div>
                {simResult && (
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => setAiBriefingMode("prospecting")}
                      className={`rounded-lg px-2 py-0.5 text-[10px] font-medium transition-colors ${
                        aiBriefingMode === "prospecting"
                          ? "bg-blue-100 text-blue-800"
                          : "border border-slate-200 text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      Prospecting
                    </button>
                    <button
                      type="button"
                      onClick={() => setAiBriefingMode("simulation")}
                      className={`rounded-lg px-2 py-0.5 text-[10px] font-medium transition-colors ${
                        aiBriefingMode === "simulation"
                          ? "bg-blue-100 text-blue-800"
                          : "border border-slate-200 text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      Simulation
                    </button>
                  </div>
                )}
              </div>
              <AIBriefingPanel
                mode={aiBriefingMode ?? "prospecting"}
                prospecting={result}
                simulation={simResult}
                onResult={setSynthesisResult}
              />
            </div>
          )}

          {/* Empty state */}
          {!result && !loading && (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white/60 p-8 text-center text-sm text-slate-400">
              Select a region preset or configure custom parameters, then run prospecting to see results.
            </div>
          )}

          {loading && (
            <LoadingProgress
              variant="prospecting"
              detail={`Screening ${candidateCount} sites · ${regionName} · ${gridSize}×${gridSize} grid`}
            />
          )}

          {exportLoading && (
            <LoadingProgress variant="export-pdf" compact />
          )}
        </div>
      </main>
    </AppShell>
  );
}
