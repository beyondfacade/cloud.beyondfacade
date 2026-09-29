import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { apiGet } from "@/shared/api/client";
import type {
  CategoryRow,
  ChildcareCenter,
  ChildcareRegionSummary,
  ConvenienceRegionSummary,
  ConvenienceStore,
  MetricKey,
  MetricRow,
  ProfileMetricKey,
  CommerceChangeMetricKey,
  RegionCommerceChangeDetail,
  RegionIndustryHourGap,
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

export function fetchMetrics(industry: string, metric: MetricKey, year: number): Promise<MetricRow[]> {
  const params = new URLSearchParams({ industry, metric, year: String(year) });
  return apiGet<MetricRow[]>(`/metrics?${params.toString()}`);
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

export function fetchChildcareSummary(regionCode: string): Promise<ChildcareRegionSummary> {
  const params = new URLSearchParams({ region: regionCode });
  return apiGet<ChildcareRegionSummary>(`/childcare-center-stats/summary?${params.toString()}`);
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

/** 동 단위 분기 지표 — 분기를 생략하면 백엔드가 최신 분기를 쓴다. 업종 파라미터가 없다. */
export function fetchCommerceChangeMetrics(
  metric: CommerceChangeMetricKey,
  yearQuarter?: string,
): Promise<MetricRow[]> {
  const params = new URLSearchParams({ metric });
  if (yearQuarter) params.set("year_quarter", yearQuarter);
  return apiGet<MetricRow[]>(`/commerce-changes?${params.toString()}`);
}

/** 유형 단계구분도 — 범주 계약. 분기를 생략하면 최신 분기. 업종 파라미터가 없다. */
export function fetchProfileTypes(yearQuarter?: string): Promise<CategoryRow[]> {
  const query = yearQuarter ? `?${new URLSearchParams({ year_quarter: yearQuarter })}` : "";
  return apiGet<CategoryRow[]>(`/profiles/types${query}`);
}

/** 파생 지표 단계구분도 — 숫자 계약(GET /profiles?metric=). 분기를 생략하면 최신 분기. 업종 파라미터가 없다. */
export function fetchProfileMetrics(metric: ProfileMetricKey, yearQuarter?: string): Promise<MetricRow[]> {
  const params = new URLSearchParams({ metric });
  if (yearQuarter) params.set("year_quarter", yearQuarter);
  return apiGet<MetricRow[]>(`/profiles?${params.toString()}`);
}

/** 동별 상권 변화 상세 — 분기를 생략하면 그 동의 최신 분기, 서울 평균 동봉. */
export function fetchCommerceChangeDetail(regionCode: string, yearQuarter?: string): Promise<RegionCommerceChangeDetail> {
  const query = yearQuarter ? `?${new URLSearchParams({ year_quarter: yearQuarter })}` : "";
  return apiGet<RegionCommerceChangeDetail>(`/commerce-changes/${regionCode}${query}`);
}

/** 시간대 어긋남 — 분기를 생략하면 그 동×업종의 최신 분기(20254까지). 매출 자료가 없는 조합은 404. */
export function fetchHourGaps(regionCode: string, industry: string, yearQuarter?: string): Promise<RegionIndustryHourGap> {
  const params = new URLSearchParams({ region: regionCode, industry });
  if (yearQuarter) params.set("year_quarter", yearQuarter);
  return apiGet<RegionIndustryHourGap>(`/hour-gaps?${params.toString()}`);
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
