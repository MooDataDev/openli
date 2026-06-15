"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";

import type { Poi } from "@/lib/types";
import { titleCase } from "@/lib/utils";

type PoiMapProps = {
  pois: Poi[];
  onViewportPoisChange?: (pois: Poi[]) => void;
};

const EMPTY_FEATURE_COLLECTION = {
  type: "FeatureCollection",
  features: [],
};

const GROUP_COLORS = [
  "#38bdf8",
  "#22c55e",
  "#f59e0b",
  "#a855f7",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#84cc16",
  "#6366f1",
  "#ef4444",
  "#06b6d4",
  "#eab308",
];

function colorForGroup(groupKey: string | null) {
  if (!groupKey) return "#64748b";

  let hash = 0;
  for (const character of groupKey) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return GROUP_COLORS[hash % GROUP_COLORS.length];
}

function buildGeojson(pois: Poi[]) {
  return {
    type: "FeatureCollection",
    features: pois.map((poi) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [poi.lon, poi.lat],
      },
        properties: {
          id: poi.id,
          name: poi.name,
          country: poi.country,
          city: poi.city,
          amenity: titleCase(poi.amenity),
          cuisine: poi.cuisineGroup || "Unknown cuisine",
          groupKey: poi.cuisineGroupKey || "unknown",
          markerColor: colorForGroup(poi.cuisineGroupKey),
          hasWebsite: poi.hasWebsite ? "Website" : "No website",
          hasMenuUrl: poi.hasMenuUrl ? "Menu" : "No menu",
          websiteUrl: poi.websiteUrl || "",
          menuUrl: poi.menuUrl || "",
        },
    })),
  };
}

function fitToPois(map: MapLibreMap, pois: Poi[]) {
  if (pois.length === 0) return;

  const bounds = new maplibregl.LngLatBounds();
  pois.forEach((poi) => bounds.extend([poi.lon, poi.lat]));
  map.fitBounds(bounds, { padding: 70, maxZoom: 8, duration: 650 });
}

function normalizeHref(value: unknown) {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (/^(yes|no|unknown|none)$/i.test(trimmed)) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (/^\/\//.test(trimmed)) return `https:${trimmed}`;
  if (!trimmed.includes(".")) return "";
  return `https://${trimmed}`;
}

function appendText(parent: HTMLElement, text: string, style: Partial<CSSStyleDeclaration> = {}) {
  const element = document.createElement("div");
  element.textContent = text;
  Object.assign(element.style, style);
  parent.appendChild(element);
}

function linkOrText(label: string, url: unknown) {
  const href = normalizeHref(url);
  if (!href) {
    const text = document.createElement("span");
    text.textContent = label;
    return text;
  }

  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener noreferrer nofollow";
  link.textContent = label;
  link.style.color = "#7dd3fc";
  link.style.textDecoration = "underline";
  link.style.textUnderlineOffset = "2px";
  return link;
}

function popupContent(properties: Record<string, unknown>) {
  const root = document.createElement("div");
  root.style.display = "grid";
  root.style.gap = "4px";

  appendText(root, String(properties.name ?? ""), {
    fontWeight: "700",
    fontSize: "13px",
  });
  appendText(root, `${String(properties.city ?? "")}, ${String(properties.country ?? "")}`, {
    color: "#94a3b8",
    fontSize: "12px",
  });
  appendText(root, `${String(properties.amenity ?? "")} · ${String(properties.cuisine ?? "Unknown cuisine")}`, {
    color: "#cbd5e1",
    fontSize: "12px",
  });

  const linkRow = document.createElement("div");
  linkRow.style.color = "#7dd3fc";
  linkRow.style.fontSize = "12px";
  linkRow.appendChild(linkOrText(String(properties.hasWebsite ?? "No website"), properties.websiteUrl));
  linkRow.append(" · ");
  linkRow.appendChild(linkOrText(String(properties.hasMenuUrl ?? "No menu"), properties.menuUrl));
  root.appendChild(linkRow);

  return root;
}

export default function PoiMap({ pois, onViewportPoisChange }: PoiMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const loadedRef = useRef(false);
  const poisRef = useRef<Poi[]>(pois);

  useEffect(() => {
    poisRef.current = pois;
  }, [pois]);

  const geojson = useMemo(() => buildGeojson(pois), [pois]);
  const legendItems = useMemo(() => {
    const counts = new Map<string, { key: string | null; label: string; count: number }>();
    pois.forEach((poi) => {
      const label = poi.cuisineGroup || "Unknown cuisine";
      const existing = counts.get(label);
      if (existing) {
        existing.count += 1;
      } else {
        counts.set(label, {
          key: poi.cuisineGroupKey,
          label,
          count: 1,
        });
      }
    });
    return [...counts.values()].sort((a, b) => b.count - a.count).slice(0, 6);
  }, [pois]);

  const updateViewportPois = useCallback(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current || !onViewportPoisChange) return;

    const bounds = map.getBounds();
    onViewportPoisChange(
      poisRef.current.filter((poi) => bounds.contains([poi.lon, poi.lat])),
    );
  }, [onViewportPoisChange]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [11.5, 49.2],
      zoom: 4,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.on("moveend", updateViewportPois);
    map.on("zoomend", updateViewportPois);

    map.on("load", () => {
      loadedRef.current = true;
      map.addSource("pois", {
        type: "geojson",
        data: buildGeojson(poisRef.current) as never,
        cluster: true,
        clusterMaxZoom: 12,
        clusterRadius: 46,
      });

      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "pois",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": ["step", ["get", "point_count"], "#2563eb", 25, "#14b8a6", 75, "#a855f7"],
          "circle-radius": ["step", ["get", "point_count"], 18, 25, 24, 75, 32],
          "circle-stroke-color": "rgba(255,255,255,0.72)",
          "circle-stroke-width": 1.2,
        },
      });

      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "pois",
        filter: ["has", "point_count"],
        layout: {
          "text-field": "{point_count_abbreviated}",
          "text-size": 12,
        },
        paint: {
          "text-color": "#ffffff",
        },
      });

      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "pois",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": ["get", "markerColor"],
          "circle-radius": 5.5,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2,
        },
      });

      map.on("click", "clusters", async (event) => {
        const features = map.queryRenderedFeatures(event.point, { layers: ["clusters"] });
        const clusterId = features[0]?.properties?.cluster_id;
        const source = map.getSource("pois") as GeoJSONSource;
        if (clusterId === undefined) return;
        const zoom = await source.getClusterExpansionZoom(clusterId);
        map.easeTo({ center: event.lngLat, zoom });
      });

      map.on("click", "unclustered-point", (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        const coordinates = feature.geometry.coordinates.slice() as [number, number];
        const properties = feature.properties as Record<string, unknown>;

        new maplibregl.Popup({ closeButton: false, offset: 14 })
          .setLngLat(coordinates)
          .setDOMContent(popupContent(properties))
          .addTo(map);
      });

      map.on("mouseenter", "clusters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "clusters", () => {
        map.getCanvas().style.cursor = "";
      });
      map.on("mouseenter", "unclustered-point", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "unclustered-point", () => {
        map.getCanvas().style.cursor = "";
      });

      updateViewportPois();
      fitToPois(map, poisRef.current);
    });

    mapRef.current = map;

    return () => {
      map.off("moveend", updateViewportPois);
      map.off("zoomend", updateViewportPois);
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
  }, [updateViewportPois]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;

    const source = map.getSource("pois") as GeoJSONSource | undefined;
    source?.setData((geojson.features.length ? geojson : EMPTY_FEATURE_COLLECTION) as never);

    if (pois.length > 0) {
      fitToPois(map, pois);
    } else {
      onViewportPoisChange?.([]);
    }
  }, [geojson, pois, onViewportPoisChange]);

  return (
    <div className="relative h-[520px] overflow-hidden rounded-lg border border-white/10 bg-slate-950 shadow-panel xl:h-[620px]">
      <div ref={containerRef} className="h-full w-full" />
      <div className="pointer-events-none absolute left-4 top-4 rounded-lg border border-white/10 bg-slate-950/72 px-3 py-2 text-xs text-slate-300 backdrop-blur-md">
        {pois.length.toLocaleString("en-US")} visible POIs
      </div>
      {legendItems.length > 0 ? (
        <div className="pointer-events-none absolute bottom-4 left-4 max-w-[240px] rounded-lg border border-white/10 bg-slate-950/76 px-3 py-2 text-xs text-slate-300 shadow-panel backdrop-blur-md">
          <div className="mb-2 font-semibold text-slate-100">Cuisine groups</div>
          <div className="space-y-1.5">
            {legendItems.map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colorForGroup(item.key) }}
                  />
                  <span className="truncate">{item.label}</span>
                </div>
                <span className="font-medium text-slate-100">{item.count.toLocaleString("en-US")}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
