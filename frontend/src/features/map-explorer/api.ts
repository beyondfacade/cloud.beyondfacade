import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { apiGet } from "@/shared/api/client";
import type {
  ChildcareCenter,
  ChildcareRegionSummary,
  ConvenienceRegionSummary,
  ConvenienceStore,
  MetricKey,
  MetricRow,
  RegionMetricKey,
  RegionProfile,
  RegionSummary,
  Store,
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

export function fetchStores(regionCode: string, industry: string): Promise<Store[]> {
  const params = new URLSearchParams({ region: regionCode, industry });
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
  metric: RegionMetricKey,
  yearQuarter?: string,
): Promise<MetricRow[]> {
  const params = new URLSearchParams({ metric });
  if (yearQuarter) params.set("year_quarter", yearQuarter);
  return apiGet<MetricRow[]>(`/commerce-changes?${params.toString()}`);
}
