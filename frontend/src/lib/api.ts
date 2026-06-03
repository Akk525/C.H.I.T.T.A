import type {
  LayoutAnalysisRequest,
  LayoutAnalysisResponse,
  ProspectingReportExportRequest,
  ProspectingRequest,
  ProspectingResponse,
  SimulationRequest,
  SimulationResponse,
  SiteAnalysisRequest,
  SiteAnalysisResponse,
  SiteHeatmapRequest,
  SiteHeatmapResponse,
  SiteReportExportRequest,
  SynthesisRequest,
  SynthesisResponse,
} from "@/lib/types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
}

export async function fetchSiteAnalysis(
  req: SiteAnalysisRequest,
  signal?: AbortSignal,
): Promise<SiteAnalysisResponse> {
  const url = `${getApiBaseUrl()}/api/site-analysis`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Site analysis request failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return (await res.json()) as SiteAnalysisResponse;
}

export async function fetchSiteHeatmap(
  req: SiteHeatmapRequest,
  signal?: AbortSignal,
): Promise<SiteHeatmapResponse> {
  const url = `${getApiBaseUrl()}/api/site-heatmap`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      latitude: req.latitude,
      longitude: req.longitude,
      radiusKm: req.radiusKm ?? 10,
      gridSize: req.gridSize ?? 5,
    }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Site heatmap request failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return (await res.json()) as SiteHeatmapResponse;
}

export async function exportSiteReport(
  req: SiteReportExportRequest,
  signal?: AbortSignal,
): Promise<Blob> {
  const url = `${getApiBaseUrl()}/api/site-report/export`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Site report export failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return await res.blob();
}

export async function runProspecting(
  req: ProspectingRequest,
  signal?: AbortSignal,
): Promise<ProspectingResponse> {
  const url = `${getApiBaseUrl()}/api/prospecting/run`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Prospecting request failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return (await res.json()) as ProspectingResponse;
}

export async function runLayoutAnalysis(
  req: LayoutAnalysisRequest,
  signal?: AbortSignal,
): Promise<LayoutAnalysisResponse> {
  const url = `${getApiBaseUrl()}/api/layout/analyze`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Layout analysis failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return (await res.json()) as LayoutAnalysisResponse;
}

export async function exportProspectingReport(
  req: ProspectingReportExportRequest,
  signal?: AbortSignal,
): Promise<Blob> {
  const url = `${getApiBaseUrl()}/api/prospecting-report/export`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Prospecting report export failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return await res.blob();
}

export async function runAISynthesis(
  req: SynthesisRequest,
  signal?: AbortSignal,
): Promise<SynthesisResponse> {
  const url = `${getApiBaseUrl()}/api/ai/synthesize`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `AI synthesis request failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return (await res.json()) as SynthesisResponse;
}

export async function runSimulation(
  req: SimulationRequest,
  signal?: AbortSignal,
): Promise<SimulationResponse> {
  const url = `${getApiBaseUrl()}/api/simulation/run`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Simulation request failed (${res.status}): ${text || res.statusText}`,
    );
  }

  return (await res.json()) as SimulationResponse;
}
