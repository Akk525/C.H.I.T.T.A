"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { GeocodeSuggestion } from "@/lib/mapboxGeocoding";
import { geocodeAutocomplete } from "@/lib/mapboxGeocoding";
import type { LatLng } from "@/lib/types";

export function LocationSearch({
  token,
  onPick,
  placeholder = "Search a location (city, ridge, coast, plateau)…",
}: {
  token: string | null;
  onPick: (pick: { label: string; center: LatLng }) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<GeocodeSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const canSearch = useMemo(() => Boolean(token?.trim()), [token]);

  useEffect(() => {
    if (!open) return;
    if (!canSearch) return;

    const q = query.trim();
    if (q.length < 2) {
      return;
    }

    const handle = window.setTimeout(async () => {
      setLoading(true);
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      try {
        const res = await geocodeAutocomplete(
          q,
          token as string,
          abortRef.current?.signal,
        );
        setItems(res);
      } finally {
        setLoading(false);
      }
    }, 220);

    return () => window.clearTimeout(handle);
  }, [query, token, open, canSearch]);

  return (
    <div className="relative w-full">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <label className="sr-only" htmlFor="location">
            Location
          </label>
          <input
            id="location"
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none ring-0 placeholder:text-slate-400 focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100"
            placeholder={
              canSearch
                ? placeholder
                : "Set NEXT_PUBLIC_MAPBOX_TOKEN to enable search…"
            }
            value={query}
            onChange={(e) => {
              const next = e.target.value;
              setQuery(next);
              if (next.trim().length < 2) setItems([]);
            }}
            onFocus={() => setOpen(true)}
            disabled={!canSearch}
            autoComplete="off"
          />
        </div>
        <div className="hidden sm:block text-xs text-slate-500">
          {loading ? "Searching…" : "Mapbox"}
        </div>
      </div>

      {open && items.length > 0 ? (
        <div className="absolute z-50 mt-2 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          {items.map((it) => (
            <button
              type="button"
              key={it.id}
              className="w-full px-3 py-2 text-left text-sm text-slate-800 hover:bg-emerald-50"
              onClick={() => {
                onPick({ label: it.label, center: it.center });
                setQuery(it.label);
                setOpen(false);
              }}
            >
              <div className="font-medium">{it.label}</div>
              <div className="text-xs text-slate-500">
                {it.center.latitude.toFixed(4)}, {it.center.longitude.toFixed(4)}
              </div>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

