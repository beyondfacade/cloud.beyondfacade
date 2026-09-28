"use client";

import { useEffect, useRef, type RefObject } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Popup,
  type Map as MapLibreGLMap,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import { readAccentColor } from "@/shared/lib/accent-color";
import { markerStrategyOf, type MarkerPoint, type MarkerStrategy } from "./marker-strategies";

const EMPTY_FEATURE_COLLECTION: FeatureCollection<Point, MarkerPoint> = { type: "FeatureCollection", features: [] };

function toGeoJSON(items: MarkerPoint[]): FeatureCollection<Point, MarkerPoint> {
  return {
    type: "FeatureCollection",
    features: items.map((item) => ({
      type: "Feature",
      properties: item,
      geometry: { type: "Point", coordinates: [item.lng, item.lat] },
    })),
  };
}

/** maplibre paint 속성은 WebGL로 렌더링돼 브라우저 CSS의 var()를 이해하지 못한다 — 반드시 계산된 값을 문자열로 넘겨야 한다.
 *  (버튼/팝업 등 실제 DOM 스타일에는 var()를 그대로 써도 된다 — 거기서만 브라우저가 해석한다.) */
function readCssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

interface LayerIds {
  source: string;
  cluster: string;
  count: string;
  point: string;
}

function applyThemeColors(map: MapLibreGLMap, ids: LayerIds, color: () => string) {
  const accent = color();
  const surface = readCssVar("--bg-surface", "#ffffff");
  const accentFg = readCssVar("--accent-fg", "#ffffff");
  if (map.getLayer(ids.cluster)) {
    map.setPaintProperty(ids.cluster, "circle-color", accent);
    map.setPaintProperty(ids.cluster, "circle-stroke-color", surface);
  }
  if (map.getLayer(ids.count)) {
    map.setPaintProperty(ids.count, "text-color", accentFg);
  }
  if (map.getLayer(ids.point)) {
    map.setPaintProperty(ids.point, "circle-color", accent);
    map.setPaintProperty(ids.point, "circle-stroke-color", surface);
  }
}

interface RegionMarkersProps {
  mapRef: RefObject<MapLibreGLMap | null>;
  ready: boolean;
  regionCode: string | null | undefined;
  industry: string;
  /** 기본은 업종별 전략(markerStrategyOf). 폐업 레이어는 CLOSED_STORE_STRATEGY를 넘긴다. */
  strategy?: MarkerStrategy<MarkerPoint>;
  /** 한 지도에 레이어를 둘 얹으려면 소스 id가 달라야 한다. */
  sourceId?: string;
  /** 마커·클러스터 색 토큰. WebGL은 var()를 모르므로 계산값을 읽어 넘긴다. */
  colorVar?: string;
}

/** 동 선택 시에만 로드되는 클러스터 마커. 전 서울 로드는 성능상 금지 — regionCode 없으면 소스를 비운다.
 *  무엇을 조회하고 팝업에 무엇을 보여줄지는 업종별 MarkerStrategy가 결정한다(기본) — 별도 레이어는 strategy prop으로 덮어쓴다. */
export function RegionMarkers({
  mapRef, ready, regionCode, industry, strategy: strategyProp, sourceId = "markers", colorVar = "--accent",
}: RegionMarkersProps) {
  const strategy = strategyProp ?? markerStrategyOf(industry);
  const ids: LayerIds = {
    source: sourceId,
    cluster: `${sourceId}-clusters`,
    count: `${sourceId}-cluster-count`,
    point: `${sourceId}-unclustered`,
  };
  const color = () => (colorVar === "--accent" ? readAccentColor() : readCssVar(colorVar, "#c8102e"));
  // 클릭 핸들러는 map 준비 시 한 번만 등록되므로 최신 전략을 ref로 읽는다.
  const strategyRef = useRef(strategy);
  strategyRef.current = strategy;

  const { data } = useQuery({
    queryKey: strategy.queryKey(regionCode as string, industry),
    queryFn: () => strategy.fetch(regionCode as string, industry),
    enabled: ready && !!regionCode,
  });

  // 소스·레이어는 map 최초 준비 시 한 번만 추가.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || map.getSource(ids.source)) return;

    map.addSource(ids.source, {
      type: "geojson",
      data: EMPTY_FEATURE_COLLECTION,
      cluster: true,
      clusterMaxZoom: 14,
      clusterRadius: 50,
    });

    map.addLayer({
      id: ids.cluster,
      type: "circle",
      source: ids.source,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": color(),
        "circle-stroke-width": 2,
        "circle-stroke-color": readCssVar("--bg-surface", "#ffffff"),
        "circle-radius": ["step", ["get", "point_count"], 16, 10, 22, 30, 28],
      },
    });
    map.addLayer({
      id: ids.count,
      type: "symbol",
      source: ids.source,
      filter: ["has", "point_count"],
      layout: { "text-field": "{point_count_abbreviated}", "text-size": 12 },
      paint: { "text-color": readCssVar("--accent-fg", "#ffffff") },
    });
    map.addLayer({
      id: ids.point,
      type: "circle",
      source: ids.source,
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-color": color(),
        "circle-radius": 6,
        "circle-stroke-width": 1.5,
        "circle-stroke-color": readCssVar("--bg-surface", "#ffffff"),
      },
    });

    const onClusterClick = async (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0] as MapGeoJSONFeature | undefined;
      const clusterId = feature?.properties?.cluster_id;
      if (!feature || typeof clusterId !== "number" || feature.geometry.type !== "Point") return;
      const source = map.getSource<GeoJSONSource>(ids.source);
      const zoom = await source?.getClusterExpansionZoom(clusterId);
      if (typeof zoom === "number") {
        map.easeTo({ center: feature.geometry.coordinates as [number, number], zoom });
      }
    };

    const onPointClick = (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0] as MapGeoJSONFeature | undefined;
      if (!feature || feature.geometry.type !== "Point") return;
      const item = feature.properties as unknown as MarkerPoint;
      new Popup({ closeButton: false })
        .setLngLat(feature.geometry.coordinates as [number, number])
        .setDOMContent(strategyRef.current.buildPopup(item))
        .addTo(map);
    };

    const onEnter = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("click", ids.cluster, onClusterClick);
    map.on("click", ids.point, onPointClick);
    map.on("mouseenter", ids.cluster, onEnter);
    map.on("mouseleave", ids.cluster, onLeave);
    map.on("mouseenter", ids.point, onEnter);
    map.on("mouseleave", ids.point, onLeave);

    // 테마(data-theme) 전환 시 클러스터/마커 페인트 색상도 재적용 — map-view.tsx의 --accent 재적용 패턴과 동일.
    const themeObserver = new MutationObserver(() => applyThemeColors(map, ids, color));
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      themeObserver.disconnect();
      map.off("click", ids.cluster, onClusterClick);
      map.off("click", ids.point, onPointClick);
      map.off("mouseenter", ids.cluster, onEnter);
      map.off("mouseleave", ids.cluster, onLeave);
      map.off("mouseenter", ids.point, onEnter);
      map.off("mouseleave", ids.point, onLeave);
      if (map.getLayer(ids.count)) map.removeLayer(ids.count);
      if (map.getLayer(ids.cluster)) map.removeLayer(ids.cluster);
      if (map.getLayer(ids.point)) map.removeLayer(ids.point);
      if (map.getSource(ids.source)) map.removeSource(ids.source);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- ids/color는 sourceId·colorVar 파생값, 그 둘이 실질 의존성
  }, [mapRef, ready, sourceId, colorVar]);

  // regionCode 없으면 소스를 비운다(성능 가드) — 있으면 조회된 마커로 교체.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource<GeoJSONSource>(ids.source);
    if (!source) return;
    source.setData(regionCode && data ? toGeoJSON(data) : EMPTY_FEATURE_COLLECTION);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- ids는 sourceId 파생값
  }, [mapRef, ready, regionCode, data, sourceId]);

  return null;
}
