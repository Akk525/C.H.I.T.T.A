import type { LatLng } from "@/lib/types";

export type GeocodeSuggestion = {
  id: string;
  label: string;
  center: LatLng;
};

export async function geocodeAutocomplete(
  query: string,
  token: string,
  signal?: AbortSignal,
): Promise<GeocodeSuggestion[]> {
  const q = query.trim();
  if (!q) return [];

  const url = new URL(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(
      q,
    )}.json`,
  );
  url.searchParams.set("autocomplete", "true");
  url.searchParams.set("limit", "6");
  url.searchParams.set("access_token", token);

  const res = await fetch(url.toString(), { signal });
  if (!res.ok) return [];

  const data = (await res.json()) as {
    features?: Array<{
      id: string;
      place_name: string;
      center: [number, number]; // [lng, lat]
    }>;
  };

  return (
    data.features?.map((f) => ({
      id: f.id,
      label: f.place_name,
      center: { latitude: f.center[1], longitude: f.center[0] },
    })) ?? []
  );
}

