"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Map as MapLibreGLMap, setWorkerUrl, type ErrorEvent as MapErrorEvent, type GeoJSONSource, type MapSourceDataEvent, type RasterTileSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { config } from "@/shared/config";
import type { CategoryRow, MapMetricKey, MetricRow } from "@/shared/api/types";
import { useMapData } from "../hooks/use-map-data";
import { makeCategoryColorScale, makeMetricColorScale, NO_DATA_COLOR } from "../lib/metric-color";
import type { MapTheme } from "../lib/neighborhood-palette";
import { bboxOfRegion } from "../lib/region-bbox";
import { NO_CLOSURE_HISTORY_INDUSTRIES } from "../lib/map-state";
import { isVerdictMissingForIndustry } from "../lib/metric-coverage";
import { MapLegend } from "./map-legend";
import { CLOSED_STORE_STRATEGY } from "./marker-strategies";
import { RegionMarkers } from "./region-markers";
import { industryLabel, type IndustryId } from "@/shared/industries";
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
  /** 동×분기 지표의 시점. null = 최신. */
  yearQuarter: string | null;
  onSelectRegion: (code: string) => void;
  /** 최근 2년 폐업 점포 레이어 토글. 기본 꺼짐 — 켜지면 영업 마커 위에 추가로 얹는다. */
  showClosed: boolean;
}

export function MapView({ regionCode, metric, industry, year, yearQuarter, onSelectRegion, showClosed }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreGLMap | null>(null);
  const onSelectRegionRef = useRef(onSelectRegion);
  onSelectRegionRef.current = onSelectRegion;
  const [ready, setReady] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [mapFailure, setMapFailure] = useState<"initialization" | "tiles" | "source" | null>(null);
  const failedSourceRef = useRef<string | null>(null);
  const failedTilesRef = useRef(new Set<string>());

  // 편의점×판정은 백엔드가 404를 주는 조합이라 조회 자체를 끈다 — 안내 문구가 이유를 말한다.
  const verdictMissing = isVerdictMissingForIndustry(metric, industry);
  const { geojson, rows, source } = useMapData(metric, { industry, year, yearQuarter }, !verdictMissing);
  // 경계/지표 fetch 실패는 무음 빈 지도가 아니라 배너로 알린다 (side-panel의 role="alert" 관행과 일관).
  const loadError = geojson.isError || rows.isError;
  // 실 API는 데이터 미보유 업종·연도에 200 + 빈 배열을 반환한다 — 빈 지도임을 명시.
  const noData = rows.isSuccess && rows.data.length === 0;
  // 개폐업 이력이 없는 업종(스냅샷 2종·학원)의 폐업률·성장률 — 연도를 바꿔도 없다는 걸 말해 준다.
  const noClosureHistory =
    noData &&
    NO_CLOSURE_HISTORY_INDUSTRIES.has(industry as IndustryId) &&
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
      return { kind: "categorical" as const, ...makeCategoryColorScale(codes, source.palette(theme), source.order) };
    }
    const values = (data as MetricRow[]).map((row) => row.value);
    return { kind: "numeric" as const, ...makeMetricColorScale(values, source.scheme) };
  }, [rows.data, source, theme]);

  // 맵 최초 생성 — unmount 시 정리.
  useEffect(() => {
    if (!containerRef.current) return;

    // Avoid constructing a partial MapLibre instance when WebGL2 is unavailable. MapLibre 6
    // returns early in this case, and its remove() cannot clean up an instance without painter.
    const probe = document.createElement("canvas");
    let supportsWebGL2 = false;
    try {
      const context = probe.getContext("webgl2");
      supportsWebGL2 = !!context;
      try { context?.getExtension("WEBGL_lose_context")?.loseContext(); } catch { /* Extension unavailable. */ }
    } catch { /* Context creation failed. */ }
    probe.width = 0;
    probe.height = 0;
    if (!supportsWebGL2) {
      setMapFailure("initialization");
      return;
    }

    let map: MapLibreGLMap;
    try {
      map = new MapLibreGLMap({
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
    } catch {
      containerRef.current.replaceChildren();
      setMapFailure("initialization");
      return;
    }
    // MapLibre 6 fires GPUInitializationError during construction and returns early when
    // WebGL2 is unavailable. That synchronous event precedes any map.on("error") listener.
    try {
      if (!map.getCanvas().getContext("webgl2")) {
        containerRef.current.replaceChildren();
        setMapFailure("initialization");
        return;
      }
    } catch {
      containerRef.current.replaceChildren();
      setMapFailure("initialization");
      return;
    }
    mapRef.current = map;
    let active = true;

    map.on("error", (event: MapErrorEvent & { sourceId?: string; tile?: { tileID?: { key?: string } } }) => {
      if (!active) return;
      const error = event.error as Error & { name?: string };
      if (error.name === "AbortError" || /\babort(?:ed|ing)?\b/i.test(error.message)) return;
      failedSourceRef.current = event.sourceId ?? null;
      if (event.sourceId === TILE_SOURCE_ID) {
        const key = event.tile?.tileID?.key;
        if (key) failedTilesRef.current.add(key);
      } else {
        failedTilesRef.current.clear();
      }
      setMapFailure(event.sourceId === TILE_SOURCE_ID ? "tiles" : event.sourceId ? "source" : "initialization");
    });
    map.on("sourcedata", (event: MapSourceDataEvent) => {
      if (!active || event.sourceId !== failedSourceRef.current) return;
      if (event.sourceId === TILE_SOURCE_ID) {
        if (event.tile?.state !== "loaded" || !event.coord?.key) return;
        failedTilesRef.current.delete(event.coord.key);
        if (failedTilesRef.current.size > 0) return;
      } else if (event.sourceDataType !== "content") return;
      failedSourceRef.current = null;
      setMapFailure(null);
    });
    map.on("sourcedataabort", (event: MapSourceDataEvent) => {
      if (!active || event.sourceId !== TILE_SOURCE_ID || failedSourceRef.current !== TILE_SOURCE_ID) return;
      const key = event.coord?.key ?? event.tile?.tileID?.key;
      if (!key || !failedTilesRef.current.delete(key)) return;
      if (failedTilesRef.current.size === 0) {
        failedSourceRef.current = null;
        setMapFailure(null);
      }
    });
    map.on("webglcontextlost", () => {
      if (active) {
        failedSourceRef.current = null;
        failedTilesRef.current.clear();
        setMapFailure("initialization");
      }
    });
    map.on("webglcontextrestored", () => {
      if (active) setMapFailure(null);
    });

    map.on("load", () => {
      if (!active) return;
      try {
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
      } catch {
        setMapFailure("initialization");
      }
    });

    return () => {
      active = false;
      map.remove();
      if (mapRef.current === map) mapRef.current = null;
    };
  }, [retryCount]);

  // 테마 전환(data-theme) → 래스터 타일 URL 교체 + 선택 강조색(--accent) 재적용.
  useEffect(() => {
    function applyTheme() {
      const map = mapRef.current;
      if (!map) return;
      const source = map.getSource<RasterTileSource>(TILE_SOURCE_ID);
      source?.setTiles([vworldTileUrl(currentTheme())]);
      if (failedSourceRef.current === TILE_SOURCE_ID) {
        failedSourceRef.current = null;
        failedTilesRef.current.clear();
        setMapFailure(null);
      }
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

  const retryMap = () => {
    const map = mapRef.current;
    const failedSource = failedSourceRef.current;
    try {
      if (map && failedSource === TILE_SOURCE_ID) {
        map.refreshTiles(TILE_SOURCE_ID);
        return;
      }
      if (map && failedSource === REGIONS_SOURCE_ID && geojson.data) {
        const source = map.getSource<GeoJSONSource>(REGIONS_SOURCE_ID);
        if (source) {
          source.setData(geojson.data);
          return;
        }
      }
    } catch {
      // A source that cannot be refreshed needs a new map instance.
    }
    failedSourceRef.current = null;
    failedTilesRef.current.clear();
    setReady(false);
    setMapFailure(null);
    setRetryCount((count) => count + 1);
  };

  return (
    <div className="relative h-full min-h-[320px] w-full">
      <div ref={containerRef} className="h-full w-full" />
      {mapFailure && (
        <div role="alert" className="absolute top-3 left-1/2 z-10 flex w-[min(90%,24rem)] -translate-x-1/2 flex-col gap-2 rounded-md border border-[var(--danger)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--danger)] shadow-md">
          <span>{mapFailure === "initialization" ? "지도를 시작할 수 없습니다. 브라우저의 그래픽 지원을 확인해 주세요." : mapFailure === "tiles" ? "배경 지도 타일을 불러오지 못했습니다. 연결을 확인해 주세요." : "지도 소스를 표시하지 못했습니다. 다시 시도해 주세요."}</span>
          <button type="button" className="self-start rounded border border-current px-2 py-1 font-medium" onClick={retryMap}>지도 다시 시도</button>
        </div>
      )}
      {!mapFailure && loadError && (
        <div
          role="alert"
          className="absolute top-3 left-1/2 z-10 flex w-[min(90%,24rem)] -translate-x-1/2 flex-col gap-2 rounded-md border border-[var(--danger)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-medium text-[var(--danger)] shadow-md"
        >
          <span>지도 데이터를 불러오지 못했습니다. 서버 연결을 확인해 주세요.</span>
          <button type="button" className="self-start rounded border border-current px-2 py-1" onClick={() => {
            if (geojson.isError) void geojson.refetch();
            if (rows.isError) void rows.refetch();
          }}>데이터 다시 시도</button>
        </div>
      )}
      {!mapFailure && !loadError && (noData || verdictMissing) && (
        <div
          role="status"
          className="absolute top-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-secondary)] shadow-md"
        >
          {verdictMissing
            ? `${industryLabel(industry)}은(는) 아직 판정 대상이 아닙니다 — 특화 신호가 붙으면 열립니다.`
            : noClosureHistory
              ? "이 업종의 원천에는 개폐업 이력이 없어 폐업률·성장률이 없습니다. 점포수를 선택해 보세요."
              : source.axis === "industry_latest"
                ? "이 업종의 판정이 아직 없습니다. 새벽 배치 후 다시 확인해 주세요."
              : source.axis === "region_quarter"
                ? yearQuarter ? "해당 분기의 지표 데이터가 없습니다." : "동네 지표 데이터가 없습니다."
              : metric === "store_count"
                ? "해당 업종·연도의 점포수 지표가 없습니다."
                : "해당 업종·연도의 지표 데이터가 없습니다."}
        </div>
      )}
      <MapLegend metric={metric} scale={scale} />
      <RegionMarkers mapRef={mapRef} ready={ready} regionCode={regionCode} industry={industry} />
      <RegionMarkers
        mapRef={mapRef}
        ready={ready}
        regionCode={showClosed ? regionCode : null}
        industry={industry}
        strategy={CLOSED_STORE_STRATEGY}
        sourceId="closed-markers"
        colorVar="--danger"
      />
    </div>
  );
}
