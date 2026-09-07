"use client";

import { useEffect, useRef, useState } from "react";
import { Map as MapLibreGLMap, setWorkerUrl, type GeoJSONSource, type RasterTileSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { config } from "@/shared/config";
import type { MetricKey } from "@/shared/api/types";
import { useMapData } from "../hooks/use-map-data";
import { makeMetricColorScale, NO_DATA_COLOR, type ColorScheme } from "../lib/metric-color";
import { StoreMarkers } from "./store-markers";

// maplibre-gl은 GeoJSON 타일링을 Web Worker에서 수행하며, 워커 스크립트 URL을 import.meta.url 기반으로
// 런타임에 자체 계산한다. Turbopack 번들 청크의 import.meta.url은 http(s) URL이 아니어서 그 계산이
// 실패해(빈 문자열) 워커가 뜨지 못하고 폴리곤 타일링이 조용히 멈춘다(콘솔/네트워크 에러 없음).
// Turbopack의 new URL(path, import.meta.url) 정적 에셋 처리는 참조된 .mjs 파일을 해시된 이름으로
// 그대로 복사할 뿐, 그 파일 내부의 상대 import("./maplibre-gl-shared.mjs")는 재작성하지 않는다.
// 그래서 원본 이름을 유지한 채 두 파일(worker + shared)을 public/에 함께 두고 그 경로를 지정한다.
setWorkerUrl("/maplibre-gl/maplibre-gl-worker.mjs");

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

/** 현재 테마의 --accent CSS 토큰을 읽는다. 토큰을 못 읽는 예외 상황의 안전 폴백은 lib의 중립색을 재사용.
 *  store-markers.tsx도 클러스터/마커 페인트 색상에 동일 토큰을 써야 하므로 export한다. */
export function readAccentColor(): string {
  return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || NO_DATA_COLOR;
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
        paint: { "fill-color": NO_DATA_COLOR, "fill-opacity": 0.55 },
      });
      map.addLayer({
        id: REGIONS_LINE_LAYER_ID,
        type: "line",
        source: REGIONS_SOURCE_ID,
        filter: ["==", ["get", "region_code"], NO_SELECTION],
        paint: { "line-color": readAccentColor(), "line-width": 2 },
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

  // 테마 전환(data-theme) → 래스터 타일 URL 교체 + 선택 강조색(--accent) 재적용.
  useEffect(() => {
    function applyTheme() {
      const map = mapRef.current;
      if (!map) return;
      const source = map.getSource<RasterTileSource>(TILE_SOURCE_ID);
      source?.setTiles([vworldTileUrl(currentTheme())]);
      if (map.getLayer(REGIONS_LINE_LAYER_ID)) {
        map.setPaintProperty(REGIONS_LINE_LAYER_ID, "line-color", readAccentColor());
      }
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
    const colorOf = makeMetricColorScale(values, scheme);
    const pairs = (rows.data ?? []).flatMap((row) => [row.region_code, colorOf(row.value)]);
    const expression = pairs.length > 0 ? ["match", ["get", "region_code"], ...pairs, NO_DATA_COLOR] : NO_DATA_COLOR;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 동적 match 표현식은 스타일 스펙 제네릭과 정확히 맞추기 어려움
    map.setPaintProperty(REGIONS_FILL_LAYER_ID, "fill-color", expression as any);
  }, [ready, rows.data, metric]);

  // 선택된 region 강조 — line 레이어 필터/색상 갱신.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setPaintProperty(REGIONS_LINE_LAYER_ID, "line-color", readAccentColor());
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- FilterSpecification은 maplibre-gl 공개 API로 노출되지 않음
    map.setFilter(REGIONS_LINE_LAYER_ID, ["==", ["get", "region_code"], regionCode ?? NO_SELECTION] as any);
  }, [ready, regionCode]);

  return (
    <div ref={containerRef} className="h-full min-h-[320px] w-full">
      <StoreMarkers mapRef={mapRef} ready={ready} regionCode={regionCode} industry={industry} />
    </div>
  );
}
