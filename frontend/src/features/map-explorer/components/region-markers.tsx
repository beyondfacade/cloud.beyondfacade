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
import { readAccentColor } from "./map-view";
import { markerStrategyOf, type MarkerPoint } from "./marker-strategies";

const MARKERS_SOURCE_ID = "markers";
const CLUSTER_LAYER_ID = "markers-clusters";
const CLUSTER_COUNT_LAYER_ID = "markers-cluster-count";
const UNCLUSTERED_LAYER_ID = "markers-unclustered";

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

function applyThemeColors(map: MapLibreGLMap) {
  const accent = readAccentColor();
  const surface = readCssVar("--bg-surface", "#ffffff");
  const accentFg = readCssVar("--accent-fg", "#ffffff");
  if (map.getLayer(CLUSTER_LAYER_ID)) {
    map.setPaintProperty(CLUSTER_LAYER_ID, "circle-color", accent);
    map.setPaintProperty(CLUSTER_LAYER_ID, "circle-stroke-color", surface);
  }
  if (map.getLayer(CLUSTER_COUNT_LAYER_ID)) {
    map.setPaintProperty(CLUSTER_COUNT_LAYER_ID, "text-color", accentFg);
  }
  if (map.getLayer(UNCLUSTERED_LAYER_ID)) {
    map.setPaintProperty(UNCLUSTERED_LAYER_ID, "circle-color", accent);
    map.setPaintProperty(UNCLUSTERED_LAYER_ID, "circle-stroke-color", surface);
  }
}

interface RegionMarkersProps {
  mapRef: RefObject<MapLibreGLMap | null>;
  ready: boolean;
  regionCode: string | null | undefined;
  industry: string;
}

/** 동 선택 시에만 로드되는 클러스터 마커. 전 서울 로드는 성능상 금지 — regionCode 없으면 소스를 비운다.
 *  무엇을 조회하고 팝업에 무엇을 보여줄지는 업종별 MarkerStrategy가 결정한다. */
export function RegionMarkers({ mapRef, ready, regionCode, industry }: RegionMarkersProps) {
  const strategy = markerStrategyOf(industry);
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
    if (!map || !ready || map.getSource(MARKERS_SOURCE_ID)) return;

    map.addSource(MARKERS_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_FEATURE_COLLECTION,
      cluster: true,
      clusterMaxZoom: 14,
      clusterRadius: 50,
    });

    map.addLayer({
      id: CLUSTER_LAYER_ID,
      type: "circle",
      source: MARKERS_SOURCE_ID,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": readAccentColor(),
        "circle-stroke-width": 2,
        "circle-stroke-color": readCssVar("--bg-surface", "#ffffff"),
        "circle-radius": ["step", ["get", "point_count"], 16, 10, 22, 30, 28],
      },
    });
    map.addLayer({
      id: CLUSTER_COUNT_LAYER_ID,
      type: "symbol",
      source: MARKERS_SOURCE_ID,
      filter: ["has", "point_count"],
      layout: { "text-field": "{point_count_abbreviated}", "text-size": 12 },
      paint: { "text-color": readCssVar("--accent-fg", "#ffffff") },
    });
    map.addLayer({
      id: UNCLUSTERED_LAYER_ID,
      type: "circle",
      source: MARKERS_SOURCE_ID,
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-color": readAccentColor(),
        "circle-radius": 6,
        "circle-stroke-width": 1.5,
        "circle-stroke-color": readCssVar("--bg-surface", "#ffffff"),
      },
    });

    const onClusterClick = async (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0] as MapGeoJSONFeature | undefined;
      const clusterId = feature?.properties?.cluster_id;
      if (!feature || typeof clusterId !== "number" || feature.geometry.type !== "Point") return;
      const source = map.getSource<GeoJSONSource>(MARKERS_SOURCE_ID);
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

    map.on("click", CLUSTER_LAYER_ID, onClusterClick);
    map.on("click", UNCLUSTERED_LAYER_ID, onPointClick);
    map.on("mouseenter", CLUSTER_LAYER_ID, onEnter);
    map.on("mouseleave", CLUSTER_LAYER_ID, onLeave);
    map.on("mouseenter", UNCLUSTERED_LAYER_ID, onEnter);
    map.on("mouseleave", UNCLUSTERED_LAYER_ID, onLeave);

    // 테마(data-theme) 전환 시 클러스터/마커 페인트 색상도 재적용 — map-view.tsx의 --accent 재적용 패턴과 동일.
    const themeObserver = new MutationObserver(() => applyThemeColors(map));
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      themeObserver.disconnect();
      map.off("click", CLUSTER_LAYER_ID, onClusterClick);
      map.off("click", UNCLUSTERED_LAYER_ID, onPointClick);
      map.off("mouseenter", CLUSTER_LAYER_ID, onEnter);
      map.off("mouseleave", CLUSTER_LAYER_ID, onLeave);
      map.off("mouseenter", UNCLUSTERED_LAYER_ID, onEnter);
      map.off("mouseleave", UNCLUSTERED_LAYER_ID, onLeave);
      if (map.getLayer(CLUSTER_COUNT_LAYER_ID)) map.removeLayer(CLUSTER_COUNT_LAYER_ID);
      if (map.getLayer(CLUSTER_LAYER_ID)) map.removeLayer(CLUSTER_LAYER_ID);
      if (map.getLayer(UNCLUSTERED_LAYER_ID)) map.removeLayer(UNCLUSTERED_LAYER_ID);
      if (map.getSource(MARKERS_SOURCE_ID)) map.removeSource(MARKERS_SOURCE_ID);
    };
  }, [mapRef, ready]);

  // regionCode 없으면 소스를 비운다(성능 가드) — 있으면 조회된 마커로 교체.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource<GeoJSONSource>(MARKERS_SOURCE_ID);
    if (!source) return;
    source.setData(regionCode && data ? toGeoJSON(data) : EMPTY_FEATURE_COLLECTION);
  }, [mapRef, ready, regionCode, data]);

  return null;
}
