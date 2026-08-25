"use client";

import { useEffect, useRef, useState } from "react";
import { Map as MapLibreGLMap, type GeoJSONSource, type RasterTileSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { config } from "@/shared/config";
import type { MetricKey } from "@/shared/api/types";
import { useMapData } from "../hooks/use-map-data";
import { metricColor, type ColorScheme } from "../lib/metric-color";

const SEOUL_CENTER: [number, number] = [126.99, 37.55];
const INITIAL_ZOOM = 11;

const TILE_SOURCE_ID = "vworld";
const TILE_LAYER_ID = "vworld-base";
const REGIONS_SOURCE_ID = "regions";
const REGIONS_FILL_LAYER_ID = "regions-fill";
const REGIONS_LINE_LAYER_ID = "regions-line";
const NO_SELECTION = "__none__";

const SCHEME_BY_METRIC: Record<MetricKey, ColorScheme> = {
  closure_rate: "sequential",
  growth_rate: "diverging",
  store_count: "sequential",
};

function currentTheme(): "light" | "dark" {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function vworldTileUrl(theme: "light" | "dark"): string {
  const layer = theme === "dark" ? "midnight" : "Base";
  return `https://api.vworld.kr/req/wmts/1.0.0/${config.vworldKey}/${layer}/{z}/{y}/{x}.png`;
}

function domainOf(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  return min === max ? [min, min + 1] : [min, max];
}

interface MapViewProps {
  regionCode?: string | null;
  metric: MetricKey;
  industry: string;
  year: number;
  onSelectRegion: (code: string) => void;
}

export function MapView({ regionCode, metric, industry, year, onSelectRegion }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreGLMap | null>(null);
  const onSelectRegionRef = useRef(onSelectRegion);
  onSelectRegionRef.current = onSelectRegion;
  const [ready, setReady] = useState(false);

  const { geojson, rows } = useMapData(metric, industry, year);

  // 맵 최초 생성 — unmount 시 정리.
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new MapLibreGLMap({
      container: containerRef.current,
      center: SEOUL_CENTER,
      zoom: INITIAL_ZOOM,
      style: {
        version: 8,
        sources: {
          [TILE_SOURCE_ID]: {
            type: "raster",
            tiles: [vworldTileUrl(currentTheme())],
            tileSize: 256,
            attribution: "© VWorld",
          },
        },
        layers: [{ id: TILE_LAYER_ID, type: "raster", source: TILE_SOURCE_ID }],
      },
    });
    mapRef.current = map;

    map.on("load", () => {
      map.addSource(REGIONS_SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: REGIONS_FILL_LAYER_ID,
        type: "fill",
        source: REGIONS_SOURCE_ID,
        paint: { "fill-color": "#cccccc", "fill-opacity": 0.55 },
      });
      map.addLayer({
        id: REGIONS_LINE_LAYER_ID,
        type: "line",
        source: REGIONS_SOURCE_ID,
        filter: ["==", ["get", "region_code"], NO_SELECTION],
        paint: { "line-color": "#000000", "line-width": 2 },
      });
      map.on("click", REGIONS_FILL_LAYER_ID, (e) => {
        const code = e.features?.[0]?.properties?.region_code;
        if (typeof code === "string") onSelectRegionRef.current(code);
      });
      setReady(true);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // 테마 전환(data-theme) → 래스터 타일 URL 교체.
  useEffect(() => {
    function applyTheme() {
      const map = mapRef.current;
      if (!map) return;
      const source = map.getSource<RasterTileSource>(TILE_SOURCE_ID);
      source?.setTiles([vworldTileUrl(currentTheme())]);
    }
    const observer = new MutationObserver(applyTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  // geojson 경계 데이터 반영.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !geojson.data) return;
    const source = map.getSource<GeoJSONSource>(REGIONS_SOURCE_ID);
    source?.setData(geojson.data);
  }, [ready, geojson.data]);

  // 단계구분도 색칠 — rows/metric 변경 시 fill-color 갱신.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const scheme = SCHEME_BY_METRIC[metric];
    const values = (rows.data ?? []).map((row) => row.value);
    const domain = domainOf(values);
    const pairs = (rows.data ?? []).flatMap((row) => [row.region_code, metricColor(row.value, domain, scheme)]);
    const expression = pairs.length > 0 ? ["match", ["get", "region_code"], ...pairs, "#cccccc"] : "#cccccc";
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 동적 match 표현식은 스타일 스펙 제네릭과 정확히 맞추기 어려움
    map.setPaintProperty(REGIONS_FILL_LAYER_ID, "fill-color", expression as any);
  }, [ready, rows.data, metric]);

  // 선택된 region 강조 — line 레이어 필터/색상 갱신.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#000000";
    map.setPaintProperty(REGIONS_LINE_LAYER_ID, "line-color", accent);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- FilterSpecification은 maplibre-gl 공개 API로 노출되지 않음
    map.setFilter(REGIONS_LINE_LAYER_ID, ["==", ["get", "region_code"], regionCode ?? NO_SELECTION] as any);
  }, [ready, regionCode]);

  return <div ref={containerRef} className="h-full w-full min-h-[480px]" />;
}
