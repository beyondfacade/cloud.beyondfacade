"use client";

import { useEffect, type RefObject } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Popup,
  type Map as MapLibreGLMap,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import { fetchStores } from "../api";
import type { Store } from "@/shared/api/types";
import { readAccentColor } from "./map-view";

const STORES_SOURCE_ID = "stores";
const CLUSTER_LAYER_ID = "stores-clusters";
const CLUSTER_COUNT_LAYER_ID = "stores-cluster-count";
const UNCLUSTERED_LAYER_ID = "stores-unclustered";

/** 영업 중으로 볼 수 있는 상태 — 그 외(폐업/취소류)는 popup에서 --danger로 표시. */
const OPEN_STATUSES = new Set(["영업", "영업중"]);

const EMPTY_FEATURE_COLLECTION: FeatureCollection<Point, Store> = { type: "FeatureCollection", features: [] };

function toGeoJSON(stores: Store[]): FeatureCollection<Point, Store> {
  return {
    type: "FeatureCollection",
    features: stores.map((store) => ({
      type: "Feature",
      properties: store,
      geometry: { type: "Point", coordinates: [store.lng, store.lat] },
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

function buildPopupContent(store: Store): HTMLDivElement {
  const container = document.createElement("div");
  container.style.color = "var(--text-primary)";
  container.style.fontSize = "0.8125rem";
  container.style.lineHeight = "1.5";

  const name = document.createElement("div");
  name.textContent = store.name;
  name.style.fontWeight = "600";
  container.appendChild(name);

  const openDate = document.createElement("div");
  openDate.textContent = `개업일 ${store.open_date}`;
  openDate.style.color = "var(--text-secondary)";
  container.appendChild(openDate);

  const status = document.createElement("div");
  status.textContent = store.status_name;
  status.style.color = OPEN_STATUSES.has(store.status_name) ? "var(--ok)" : "var(--danger)";
  status.style.fontWeight = "600";
  container.appendChild(status);

  return container;
}

interface StoreMarkersProps {
  mapRef: RefObject<MapLibreGLMap | null>;
  ready: boolean;
  regionCode: string | null | undefined;
  industry: string;
}

/** 동 선택 시에만 로드되는 점포 클러스터 마커. 전 서울 로드는 성능상 금지 — regionCode 없으면 소스를 비운다. */
export function StoreMarkers({ mapRef, ready, regionCode, industry }: StoreMarkersProps) {
  const { data } = useQuery({
    queryKey: ["stores", regionCode, industry],
    queryFn: () => fetchStores(regionCode as string, industry),
    enabled: ready && !!regionCode,
  });

  // 소스·레이어는 map 최초 준비 시 한 번만 추가.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || map.getSource(STORES_SOURCE_ID)) return;

    map.addSource(STORES_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_FEATURE_COLLECTION,
      cluster: true,
      clusterMaxZoom: 14,
      clusterRadius: 50,
    });

    map.addLayer({
      id: CLUSTER_LAYER_ID,
      type: "circle",
      source: STORES_SOURCE_ID,
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
      source: STORES_SOURCE_ID,
      filter: ["has", "point_count"],
      layout: { "text-field": "{point_count_abbreviated}", "text-size": 12 },
      paint: { "text-color": readCssVar("--accent-fg", "#ffffff") },
    });
    map.addLayer({
      id: UNCLUSTERED_LAYER_ID,
      type: "circle",
      source: STORES_SOURCE_ID,
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
      const source = map.getSource<GeoJSONSource>(STORES_SOURCE_ID);
      const zoom = await source?.getClusterExpansionZoom(clusterId);
      if (typeof zoom === "number") {
        map.easeTo({ center: feature.geometry.coordinates as [number, number], zoom });
      }
    };

    const onPointClick = (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0] as MapGeoJSONFeature | undefined;
      if (!feature || feature.geometry.type !== "Point") return;
      const store = feature.properties as unknown as Store;
      new Popup({ closeButton: false })
        .setLngLat(feature.geometry.coordinates as [number, number])
        .setDOMContent(buildPopupContent(store))
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
      if (map.getSource(STORES_SOURCE_ID)) map.removeSource(STORES_SOURCE_ID);
    };
  }, [mapRef, ready]);

  // regionCode 없으면 소스를 비운다(성능 가드) — 있으면 조회된 점포로 교체.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource<GeoJSONSource>(STORES_SOURCE_ID);
    if (!source) return;
    source.setData(regionCode && data ? toGeoJSON(data) : EMPTY_FEATURE_COLLECTION);
  }, [mapRef, ready, regionCode, data]);

  return null;
}
