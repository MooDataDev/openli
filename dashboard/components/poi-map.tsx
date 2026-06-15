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
          cuisineRaw: poi.cuisineRaw || poi.cuisine || "",
          hasWebsite: poi.hasWebsite ? "Website" : "No website",
          hasMenuUrl: poi.hasMenuUrl ? "Menu" : "No menu",
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

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
          "circle-color": "#38bdf8",
          "circle-radius": 5,
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
        const properties = feature.properties as Record<string, string>;
        const rawCuisine = properties.cuisineRaw ? escapeHtml(properties.cuisineRaw) : "";

        new maplibregl.Popup({ closeButton: false, offset: 14 })
          .setLngLat(coordinates)
          .setHTML(
            `<div class="space-y-1">
              <div style="font-weight:700;font-size:13px">${escapeHtml(properties.name)}</div>
              <div style="color:#94a3b8;font-size:12px">${escapeHtml(properties.city)}, ${escapeHtml(properties.country)}</div>
              <div style="color:#cbd5e1;font-size:12px">${escapeHtml(properties.amenity)} · ${escapeHtml(properties.cuisine)}</div>
              ${rawCuisine ? `<div style="color:#94a3b8;font-size:11px">Raw: ${rawCuisine}</div>` : ""}
              <div style="color:#7dd3fc;font-size:12px">${escapeHtml(properties.hasWebsite)} · ${escapeHtml(properties.hasMenuUrl)}</div>
            </div>`,
          )
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
    </div>
  );
}
