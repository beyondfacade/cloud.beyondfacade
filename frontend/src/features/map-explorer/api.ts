import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { apiGet } from "@/shared/api/client";
import type {
  CategoryRow,
  ChildcareCenter,
  ConvenienceRegionSummary,
  ConvenienceStore,
  RegionIndustryVerdict,
  VerdictAlternatives,
  RegionProfile,
  RegionSummary,
  Store,
  VerdictRow,
} from "@/shared/api/types";

export type RegionProperties = { region_code: string; name: string };
export type RegionGeoJSON = FeatureCollection<Polygon | MultiPolygon, RegionProperties>;

export function fetchRegionsGeoJson(): Promise<RegionGeoJSON> {
  return apiGet<RegionGeoJSON>("/regions/geojson");
}

export function fetchRegionSummary(regionCode: string, industry: string): Promise<RegionSummary> {
  const params = new URLSearchParams({ industry });
  return apiGet<RegionSummary>(`/regions/${regionCode}/summary?${params.toString()}`);
}

export type StoreStatus = "open" | "closed";

/** 점포 마커 — status=closed는 최근 2년 폐업(백엔드 창). 기본 open은 기존 계약 그대로. */
export function fetchStores(regionCode: string, industry: string, status: StoreStatus = "open"): Promise<Store[]> {
  const params = new URLSearchParams({ region: regionCode, industry, status });
  return apiGet<Store[]>(`/stores?${params.toString()}`);
}

export function fetchChildcareCenters(regionCode: string): Promise<ChildcareCenter[]> {
  const params = new URLSearchParams({ region: regionCode });
  return apiGet<ChildcareCenter[]>(`/childcare-centers?${params.toString()}`);
}

export function fetchConvenienceStores(regionCode: string): Promise<ConvenienceStore[]> {
  const params = new URLSearchParams({ region: regionCode });
  return apiGet<ConvenienceStore[]>(`/convenience-stores?${params.toString()}`);
}

export function fetchConvenienceSummary(regionCode: string): Promise<ConvenienceRegionSummary> {
  const params = new URLSearchParams({ region: regionCode });
  return apiGet<ConvenienceRegionSummary>(`/convenience-stores/summary?${params.toString()}`);
}

/** 동네 프로필 — 분기를 생략하면 백엔드가 그 동의 최신 분기를 준다 (화면은 최신이 언제인지 모른다). */
export function fetchRegionProfile(regionCode: string, yearQuarter?: string): Promise<RegionProfile> {
  const query = yearQuarter ? `?${new URLSearchParams({ year_quarter: yearQuarter })}` : "";
  return apiGet<RegionProfile>(`/profiles/${regionCode}${query}`);
}

/** 위험도 단계구분도 — 실 API는 {region_code, value}로 주지만 범주 파이프라인(type_code)으로 옮긴다 (작은 ACL). 시점 파라미터 없음(배치 최신). */
export function fetchVerdictMetrics(industry: string): Promise<CategoryRow[]> {
  const params = new URLSearchParams({ industry });
  return apiGet<VerdictRow[]>(`/verdicts?${params.toString()}`).then((rows) =>
    rows.map(({ region_code, value }) => ({ region_code, type_code: value })),
  );
}

/** 판정 카드 단건 — 판정 대상이 아니면 INDUSTRY_NOT_FOUND, 배치 전·모르는 동이면 VERDICT_NOT_FOUND. */
export function fetchVerdict(regionCode: string, industry: string): Promise<RegionIndustryVerdict> {
  const params = new URLSearchParams({ industry });
  return apiGet<RegionIndustryVerdict>(`/verdicts/${regionCode}?${params.toString()}`);
}

/** 대안 두 축 — 404 규칙은 단건과 같다. 기준이 경고 없음이면 두 목록이 모두 빈다. */
export function fetchVerdictAlternatives(regionCode: string, industry: string): Promise<VerdictAlternatives> {
  const params = new URLSearchParams({ industry });
  return apiGet<VerdictAlternatives>(`/verdicts/${regionCode}/alternatives?${params.toString()}`);
}
