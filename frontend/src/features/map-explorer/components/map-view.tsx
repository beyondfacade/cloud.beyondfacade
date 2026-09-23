"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Map as MapLibreGLMap, setWorkerUrl, type GeoJSONSource, type RasterTileSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { config } from "@/shared/config";
import type { CategoryRow, MapMetricKey, MetricRow } from "@/shared/api/types";
import { useMapData } from "../hooks/use-map-data";
import { NEIGHBORHOOD_TYPES } from "@/shared/neighborhood";
import { makeCategoryColorScale, makeMetricColorScale, NO_DATA_COLOR } from "../lib/metric-color";
import { neighborhoodPalette, type MapTheme } from "../lib/neighborhood-palette";
import { bboxOfRegion } from "../lib/region-bbox";
import { SNAPSHOT_INDUSTRIES } from "../lib/map-state";
import { MapLegend } from "./map-legend";
import { RegionMarkers } from "./region-markers";
import type { IndustryId } from "@/shared/industries";
import { readAccentColor } from "@/shared/lib/accent-color";

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

function currentTheme(): MapTheme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function vworldTileUrl(theme: "light" | "dark"): string {
  const layer = theme === "dark" ? "midnight" : "Base";
  return `https://api.vworld.kr/req/wmts/1.0.0/${config.vworldKey}/${layer}/{z}/{y}/{x}.png`;
}

interface MapViewProps {
  regionCode?: string | null;
  metric: MapMetricKey;
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

  const { geojson, rows, source } = useMapData(metric, industry, year);
  // 경계/지표 fetch 실패는 무음 빈 지도가 아니라 배너로 알린다 (side-panel의 role="alert" 관행과 일관).
  const loadError = geojson.isError || rows.isError;
  // 실 API는 데이터 미보유 업종·연도에 200 + 빈 배열을 반환한다 — 빈 지도임을 명시.
  const noData = rows.isSuccess && rows.data.length === 0;
  const snapshotNoRate =
    noData &&
    SNAPSHOT_INDUSTRIES.has(industry as IndustryId) &&
    (metric === "closure_rate" || metric === "growth_rate");

  // 범주 팔레트는 테마마다 다르다 — 테마가 바뀌면 fill-color를 다시 칠해야 하므로 상태로 든다.
  const [theme, setTheme] = useState<MapTheme>("light");
  useEffect(() => setTheme(currentTheme()), []);

  // 색상 스케일 — fill-color 페인트와 범례가 같은 경계(classes)를 공유하는 단일 원천.
  // 원천의 kind가 숫자면 분위수/발산 스케일, 범주면 범주 팔레트 — 두 함수는 섞이지 않는다.
  const scale = useMemo(() => {
    const data = rows.data ?? [];
    if (source.kind === "categorical") {
      const codes = (data as CategoryRow[]).map((row) => row.type_code);
      return { kind: "categorical" as const, ...makeCategoryColorScale(codes, neighborhoodPalette(theme), NEIGHBORHOOD_TYPES) };
    }
    const values = (data as MetricRow[]).map((row) => row.value);
    return { kind: "numeric" as const, ...makeMetricColorScale(values, source.scheme) };
  }, [rows.data, source, theme]);

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
        paint: { "line-color": readAccentColor(NO_DATA_COLOR), "line-width": 2 },
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
        map.setPaintProperty(REGIONS_LINE_LAYER_ID, "line-color", readAccentColor(NO_DATA_COLOR));
      }
      setTheme(currentTheme()); // 범주 팔레트 재적용 — scale이 theme을 의존해 fill 효과가 다시 돈다
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

  // 딥링크·선택 행정동으로 카메라 이동 (fitBounds).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !geojson.data || !regionCode) return;
    const bbox = bboxOfRegion(geojson.data as GeoJSON.FeatureCollection, regionCode);
    if (!bbox) return;
    map.fitBounds(
      [
        [bbox[0], bbox[1]],
        [bbox[2], bbox[3]],
      ],
      { padding: 64, maxZoom: 14, duration: 800 },
    );
  }, [ready, geojson.data, regionCode]);

  // 단계구분도 색칠 — rows/metric 변경 시 fill-color 갱신.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const pairs =
      scale.kind === "categorical"
        ? ((rows.data ?? []) as CategoryRow[]).flatMap((row) => [row.region_code, scale.colorOf(row.type_code)])
        : ((rows.data ?? []) as MetricRow[]).flatMap((row) => [row.region_code, scale.colorOf(row.value)]);
    const expression = pairs.length > 0 ? ["match", ["get", "region_code"], ...pairs, NO_DATA_COLOR] : NO_DATA_COLOR;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 동적 match 표현식은 스타일 스펙 제네릭과 정확히 맞추기 어려움
    map.setPaintProperty(REGIONS_FILL_LAYER_ID, "fill-color", expression as any);
  }, [ready, rows.data, scale]);

  // 선택된 region 강조 — line 레이어 필터/색상 갱신.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.setPaintProperty(REGIONS_LINE_LAYER_ID, "line-color", readAccentColor(NO_DATA_COLOR));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- FilterSpecification은 maplibre-gl 공개 API로 노출되지 않음
    map.setFilter(REGIONS_LINE_LAYER_ID, ["==", ["get", "region_code"], regionCode ?? NO_SELECTION] as any);
  }, [ready, regionCode]);

  return (
    <div className="relative h-full min-h-[320px] w-full">
      <div ref={containerRef} className="h-full w-full" />
      {loadError && (
        <div
          role="alert"
          className="absolute top-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-[var(--danger)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-medium text-[var(--danger)] shadow-md"
        >
          지도 데이터를 불러오지 못했습니다. 서버 연결을 확인해 주세요.
        </div>
      )}
      {!loadError && noData && (
        <div
          role="status"
          className="absolute top-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-secondary)] shadow-md"
        >
          {snapshotNoRate
            ? "스냅샷 원천이라 이 지표는 아직 없습니다. 점포수를 선택해 보세요."
            : metric === "store_count"
              ? "해당 업종·연도의 점포수 지표가 없습니다."
              : "해당 업종·연도의 지표 데이터가 없습니다."}
        </div>
      )}
      <MapLegend metric={metric} scale={scale} />
      <RegionMarkers mapRef={mapRef} ready={ready} regionCode={regionCode} industry={industry} />
    </div>
  );
}
