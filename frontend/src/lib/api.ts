import type {
  SiteAnalysisRequest,
  SiteAnalysisResponse,
  SiteHeatmapRequest,
  SiteHeatmapResponse,
  SiteReportExportRequest,
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
