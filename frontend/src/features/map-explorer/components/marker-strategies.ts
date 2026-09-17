import type { ChildcareCenter, ConvenienceStore, Store } from "@/shared/api/types";
import type { IndustryId } from "@/shared/industries";
import { fetchChildcareCenters, fetchConvenienceStores, fetchStores } from "../api";
import { formatOccupancy, formatWaiting } from "../lib/childcare-format";

export interface MarkerPoint {
  lat: number;
  lng: number;
}

/** 업종별 지도 마커 전략 — 무엇을 조회하고 팝업에 무엇을 보여줄지를 업종이 스스로 안다 (Strategy).
 *  메서드 문법으로 선언해 MarkerStrategy<ChildcareCenter>를 MarkerStrategy<MarkerPoint>로 담을 수 있게 한다. */
export interface MarkerStrategy<T extends MarkerPoint> {
  queryKey(regionCode: string, industry: string): readonly unknown[];
  fetch(regionCode: string, industry: string): Promise<T[]>;
  buildPopup(item: T): HTMLElement;
}

interface PopupLine {
  text: string;
  color?: string;
  bold?: boolean;
}

/** 팝업은 실제 DOM이라 var() 토큰을 그대로 쓸 수 있다 (WebGL paint 속성과 다름). */
function popupContent(lines: PopupLine[]): HTMLDivElement {
  const container = document.createElement("div");
  container.style.color = "var(--text-primary)";
  container.style.fontSize = "0.8125rem";
  container.style.lineHeight = "1.5";
  for (const line of lines) {
    const row = document.createElement("div");
    row.textContent = line.text;
    if (line.color) row.style.color = line.color;
    if (line.bold) row.style.fontWeight = "600";
    container.appendChild(row);
  }
  return container;
}

/** 영업 중으로 볼 수 있는 상태 — 그 외(폐업/취소류)는 popup에서 --danger로 표시. */
const OPEN_STATUSES = new Set(["영업", "영업중"]);

const STORE_STRATEGY: MarkerStrategy<Store> = {
  queryKey: (regionCode, industry) => ["stores", regionCode, industry],
  fetch: (regionCode, industry) => fetchStores(regionCode, industry),
  buildPopup: (store) =>
    popupContent([
      { text: store.name, bold: true },
      { text: `개업일 ${store.open_date}`, color: "var(--text-secondary)" },
      {
        text: store.status_name,
        color: OPEN_STATUSES.has(store.status_name) ? "var(--ok)" : "var(--danger)",
        bold: true,
      },
    ]),
};

const CHILDCARE_STRATEGY: MarkerStrategy<ChildcareCenter> = {
  queryKey: (regionCode) => ["childcare-centers", regionCode],
  fetch: (regionCode) => fetchChildcareCenters(regionCode),
  // maplibre는 GeoJSON 타일링 시 null 속성을 떨어뜨려 클릭된 feature에서는 undefined로 온다 — ?? 로 원천 공란과 합류.
  buildPopup: (center) =>
    popupContent([
      { text: center.name, bold: true },
      { text: `${center.type_name} · ${center.status_name ?? "상태 미상"}`, color: "var(--text-secondary)" },
      {
        text: `정원 ${center.capacity} · 현원 ${center.child_count} (${formatOccupancy(
          center.capacity > 0 ? center.child_count / center.capacity : null,
        )})`,
      },
      { text: `입소대기 ${formatWaiting(center.waiting_count ?? null)}`, color: "var(--text-secondary)" },
    ]),
};

const CONVENIENCE_STRATEGY: MarkerStrategy<ConvenienceStore> = {
  queryKey: (regionCode) => ["convenience-stores", regionCode],
  fetch: (regionCode) => fetchConvenienceStores(regionCode),
  // null 속성은 maplibre 타일링에서 떨어져 undefined로 온다 — ?? 로 원천 공란과 합류.
  buildPopup: (store) =>
    popupContent([
      { text: [store.name, store.branch_name].filter(Boolean).join(" "), bold: true },
      { text: store.brand ?? "기타 브랜드", color: "var(--text-secondary)" },
      ...(store.road_address ? [{ text: store.road_address, color: "var(--text-secondary)" }] : []),
    ]),
};

/** 전용 원천이 있는 업종만 등록 — 나머지는 store 테이블(인허가) 점포 마커. */
const STRATEGY_BY_INDUSTRY: Partial<Record<IndustryId, MarkerStrategy<MarkerPoint>>> = {
  childcare: CHILDCARE_STRATEGY,
  convenience_store: CONVENIENCE_STRATEGY,
};

export function markerStrategyOf(industry: string): MarkerStrategy<MarkerPoint> {
  return STRATEGY_BY_INDUSTRY[industry as IndustryId] ?? STORE_STRATEGY;
}
