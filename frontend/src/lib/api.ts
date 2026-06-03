import type {
  HistoryListResponse,
  SignalsQueryRequest,
  SignalsQueryResponse,
  HistorySummarizeRequest,
  HistorySummaryResponse,
  LayoutAnalysisRequest,
  LayoutAnalysisResponse,
  ProspectingReportExportRequest,
  SavedRunDetail,
  SaveRunRequest,
  SaveRunResponse,
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

// Returns {"X-Api-Key": "<key>"} when NEXT_PUBLIC_CHITTA_API_KEY is set, else {}.
// This is demo-level shared key protection — not per-user auth.
function getAuthHeaders(): Record<string, string> {
  const key = process.env.NEXT_PUBLIC_CHITTA_API_KEY?.trim();
  return key ? { "X-Api-Key": key } : {};
}

export async function fetchSiteAnalysis(
  req: SiteAnalysisRequest,
  signal?: AbortSignal,
): Promise<SiteAnalysisResponse> {
  const url = `${getApiBaseUrl()}/api/site-analysis`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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

export async function queryDevelopmentSignals(
  req: SignalsQueryRequest,
  signal?: AbortSignal,
): Promise<SignalsQueryResponse> {
  const url = `${getApiBaseUrl()}/api/signals/query`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Signals query failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as SignalsQueryResponse;
}

export async function saveToHistory(
  req: SaveRunRequest,
  signal?: AbortSignal,
): Promise<SaveRunResponse> {
  const url = `${getApiBaseUrl()}/api/history/save`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Save failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as SaveRunResponse;
}

export async function fetchHistoryRuns(
  runType?: string,
  limit = 20,
  offset = 0,
  signal?: AbortSignal,
): Promise<HistoryListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (runType) params.set("runType", runType);
  const url = `${getApiBaseUrl()}/api/history/runs?${params}`;
  const res = await fetch(url, { headers: getAuthHeaders(), signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`History fetch failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as HistoryListResponse;
}

export async function fetchHistoryRun(
  id: string,
  signal?: AbortSignal,
): Promise<SavedRunDetail> {
  const url = `${getApiBaseUrl()}/api/history/run/${id}`;
  const res = await fetch(url, { headers: getAuthHeaders(), signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Run fetch failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as SavedRunDetail;
}

export async function fetchHistoryCompare(
  idA: string,
  idB: string,
  signal?: AbortSignal,
): Promise<HistorySummaryResponse> {
  const url = `${getApiBaseUrl()}/api/history/compare/${idA}/${idB}`;
  const res = await fetch(url, { headers: getAuthHeaders(), signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Comparison failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as HistorySummaryResponse;
}

export async function runHistorySummarize(
  req: HistorySummarizeRequest,
  signal?: AbortSignal,
): Promise<HistorySummaryResponse> {
  const url = `${getApiBaseUrl()}/api/history/summarize`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Summarize failed (${res.status}): ${text || res.statusText}`);
  }
  return (await res.json()) as HistorySummaryResponse;
}

export async function runLayoutAnalysis(
  req: LayoutAnalysisRequest,
  signal?: AbortSignal,
): Promise<LayoutAnalysisResponse> {
  const url = `${getApiBaseUrl()}/api/layout/analyze`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
