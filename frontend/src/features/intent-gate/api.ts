import { apiGet, apiPost } from "@/shared/api/client";
import type { IntentResult } from "@/shared/api/types";

/** 경계 GeoJSON 중 관문이 쓰는 최소 형태 — map-explorer의 타입을 import하지 않는다 (§14 feature 간 직접 import 금지). */
interface RegionListGeoJSON {
  features: { properties: { region_code: string; name: string } }[];
}

/** 문장 → 의도 (POST /intent 첫 번째 형태). */
export function parseIntent(text: string): Promise<IntentResult> {
  return apiPost<IntentResult>("/intent", { text });
}

/** 되묻기로 완성된 코드 쌍 → 진단만 (POST /intent 두 번째 형태, 파서를 건너뛴다). */
export function diagnoseIntent(regionCode: string, industryId: string): Promise<IntentResult> {
  return apiPost<IntentResult>("/intent", { region_code: regionCode, industry_id: industryId });
}

/** 구 → 동 칩에 쓸 행정동 목록. 경계 GeoJSON을 한 번만 받아 이름·코드만 남긴다. */
export function fetchRegionList(): Promise<{ region_code: string; name: string }[]> {
  return apiGet<RegionListGeoJSON>("/regions/geojson").then((gj) => gj.features.map((f) => f.properties));
}
