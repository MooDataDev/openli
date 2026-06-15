"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Database, MapPinned, RefreshCw } from "lucide-react";

import { FilterSidebar } from "@/components/filter-sidebar";
import { KpiPanel } from "@/components/kpi-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Filters, Poi, PoiApiResponse } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/utils";

const PoiMap = dynamic(() => import("@/components/poi-map"), {
  ssr: false,
  loading: () => <div className="h-[520px] animate-pulse rounded-lg bg-slate-900/70 xl:h-[620px]" />,
});

const DashboardCharts = dynamic(() => import("@/components/charts").then((mod) => mod.DashboardCharts), {
  ssr: false,
  loading: () => <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
    <div className="h-[280px] animate-pulse rounded-lg bg-slate-900/70" />
    <div className="h-[280px] animate-pulse rounded-lg bg-slate-900/70" />
  </div>,
});

const DEFAULT_FILTERS: Filters = {
  continent: "all",
  country: "all",
  city: "all",
  amenity: "all",
  cuisine: "all",
  hasWebsite: false,
  hasMenuUrl: false,
};

function countBy(items: Poi[], key: (poi: Poi) => string | null | undefined) {
  const counts = new Map<string, number>();
  items.forEach((item) => {
    const value = key(item);
    if (!value) return;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });
  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

function applyFilters(pois: Poi[], filters: Filters) {
  return pois.filter((poi) => {
    if (filters.country !== "all" && poi.country !== filters.country) return false;
    if (filters.continent !== "all" && poi.continent !== filters.continent) return false;
    if (filters.city !== "all" && poi.city !== filters.city) return false;
    if (filters.amenity !== "all" && poi.amenity !== filters.amenity) return false;
    if (filters.cuisine !== "all" && !poi.cuisineTokens.includes(filters.cuisine)) return false;
    if (filters.hasWebsite && !poi.hasWebsite) return false;
    if (filters.hasMenuUrl && !poi.hasMenuUrl) return false;
    return true;
  });
}

function coverage(items: Poi[], field: "hasWebsite" | "hasMenuUrl") {
  if (items.length === 0) return 0;
  return items.filter((item) => item[field]).length / items.length;
}

function countCuisines(items: Poi[]) {
  const counts = new Map<string, number>();
  items.forEach((poi) => {
    if (!poi.cuisinePrimary) return;
    counts.set(poi.cuisinePrimary, (counts.get(poi.cuisinePrimary) ?? 0) + 1);
  });
  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

export default function Home() {
  const [data, setData] = useState<PoiApiResponse | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [viewportPois, setViewportPois] = useState<Poi[]>([]);
  const [hasViewportPois, setHasViewportPois] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        setLoading(true);
        const response = await fetch("/api/pois", { cache: "no-store" });
        const payload = (await response.json()) as PoiApiResponse;
        if (!response.ok) throw new Error(payload.error ?? "Failed to load POIs");
        if (!ignore) setData(payload);
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Failed to load POIs");
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  const filteredPois = useMemo(() => applyFilters(data?.pois ?? [], filters), [data?.pois, filters]);

  const handleViewportPoisChange = useCallback((pois: Poi[]) => {
    setViewportPois(pois);
    setHasViewportPois(true);
  }, []);

  const continents = data?.continents ?? [];
  const countries = useMemo(() => {
    const source = filters.continent === "all"
      ? data?.pois ?? []
      : (data?.pois ?? []).filter((poi) => poi.continent === filters.continent);
    return [...new Set(source.map((poi) => poi.country).filter((country) => country !== "Unknown"))].sort();
  }, [data?.pois, filters.continent]);
  const cities = useMemo(() => {
    const source = (data?.pois ?? []).filter((poi) => {
      if (filters.continent !== "all" && poi.continent !== filters.continent) return false;
      if (filters.country !== "all" && poi.country !== filters.country) return false;
      return true;
    });
    return [...new Set(source.map((poi) => poi.city).filter((city) => city !== "Unknown"))].sort();
  }, [data?.pois, filters.continent, filters.country]);

  const countryData = useMemo(() => countBy(filteredPois, (poi) => poi.country).slice(0, 8), [filteredPois]);
  const cuisineData = useMemo(() => countCuisines(filteredPois), [filteredPois]);
  const filteredPoiIds = useMemo(() => new Set(filteredPois.map((poi) => poi.id)), [filteredPois]);
  const visibleViewportPois = useMemo(
    () => (hasViewportPois ? viewportPois.filter((poi) => filteredPoiIds.has(poi.id)) : filteredPois),
    [filteredPoiIds, filteredPois, hasViewportPois, viewportPois],
  );
  const viewportCuisineData = useMemo(() => countCuisines(visibleViewportPois), [visibleViewportPois]);

  const restaurants = filteredPois.filter((poi) => poi.amenity === "restaurant").length;
  const websiteCoverage = coverage(filteredPois, "hasWebsite");
  const menuCoverage = coverage(filteredPois, "hasMenuUrl");
  const cityData = countBy(filteredPois, (poi) => (poi.city === "Unknown" ? null : poi.city));
  const topCuisine = cuisineData[0]?.name ?? "No cuisine data";
  const topCountry = countryData[0]?.name ?? "No country data";
  const topCity = cityData[0]?.name ?? "No city data";
  const insights = [
    `Top cuisine: ${topCuisine}`,
    `Top country: ${topCountry}`,
    `Top city: ${topCity}`,
    `Website coverage: ${formatPercent(websiteCoverage)}`,
  ];

  const snapshot = data?.snapshotDate ?? "latest";

  return (
    <main className="min-h-screen px-4 py-4 text-slate-100 sm:px-6 lg:px-8">
      <nav className="mb-4 flex flex-col gap-3 rounded-lg border border-white/10 bg-slate-950/64 px-4 py-3 shadow-panel backdrop-blur-xl md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-blue-500 text-white">
            <MapPinned className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-white">Open Location Intelligence</h1>
            <div className="text-xs text-slate-400">Snapshot {snapshot}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-300">
          <span className="rounded-md bg-blue-500/15 px-3 py-1.5 text-blue-200">Explore</span>
          <span className="hidden px-3 py-1.5 text-slate-500 md:inline">Insights</span>
          <span className="hidden px-3 py-1.5 text-slate-500 md:inline">Sources</span>
        </div>
      </nav>

      {error ? (
        <Card>
          <CardContent className="flex min-h-[320px] flex-col items-center justify-center gap-3 text-center">
            <Database className="h-10 w-10 text-rose-300" />
            <div className="text-lg font-semibold">Could not load Parquet snapshots</div>
            <div className="max-w-xl text-sm text-slate-400">{error}</div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 2xl:grid-cols-[280px_minmax(0,1fr)_360px]">
          <aside className="2xl:sticky 2xl:top-4 2xl:h-[calc(100vh-2rem)]">
            <FilterSidebar
              filters={filters}
              continents={continents}
              countries={countries}
              cities={cities}
              amenities={data?.amenities ?? []}
              cuisines={data?.cuisines ?? []}
              onChange={setFilters}
              onReset={() => setFilters(DEFAULT_FILTERS)}
            />
          </aside>

          <section className="space-y-4">
            <Card className="overflow-hidden">
              <div className="flex flex-col gap-3 border-b border-white/10 px-4 py-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="text-base font-semibold text-white">Food POI Map</div>
                  <div className="text-xs text-slate-400">
                    {loading ? "Loading local Parquet snapshots" : `${formatNumber(filteredPois.length)} of ${formatNumber(data?.pois.length ?? 0)} POIs visible`}
                  </div>
                </div>
                <Button onClick={() => setFilters(DEFAULT_FILTERS)} className="w-full md:w-auto">
                  <RefreshCw className="h-4 w-4" />
                  Clear filters
                </Button>
              </div>
              <div className="p-3">
                {loading ? (
                  <div className="h-[520px] animate-pulse rounded-lg bg-slate-900/70 xl:h-[620px]" />
                ) : (
                  <PoiMap pois={filteredPois} onViewportPoisChange={handleViewportPoisChange} />
                )}
              </div>
            </Card>
            <DashboardCharts viewportCuisineData={viewportCuisineData} cuisineData={cuisineData} />
          </section>

          <aside>
            <KpiPanel
              totalPois={filteredPois.length}
              restaurants={restaurants}
              countriesCovered={new Set(filteredPois.map((poi) => poi.country)).size}
              citiesCovered={new Set(filteredPois.map((poi) => poi.city).filter((city) => city !== "Unknown")).size}
              websiteCoverage={websiteCoverage}
              menuCoverage={menuCoverage}
              insights={insights}
            />
          </aside>
        </div>
      )}

      <footer className="mt-5 flex flex-col gap-3 border-t border-white/10 py-5 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="font-semibold text-slate-200">OpenLI</div>
          <div className="text-xs">OpenStreetMap-derived location intelligence.</div>
        </div>
        <div className="flex flex-wrap gap-4">
          <span>Imprint</span>
          <span>Privacy Policy</span>
          <span>Legal Notice</span>
          <span>Data Sources</span>
        </div>
      </footer>
    </main>
  );
}
