import type { FeatureCollection, Polygon } from "geojson";
import { apiGet } from "@/shared/api/client";
import type { MetricKey, MetricRow } from "@/shared/api/types";

export type RegionProperties = { region_code: string; name: string };
export type RegionGeoJSON = FeatureCollection<Polygon, RegionProperties>;

export function fetchRegionsGeoJson(): Promise<RegionGeoJSON> {
  return apiGet<RegionGeoJSON>("/regions/geojson");
}

export function fetchMetrics(industry: string, metric: MetricKey, year: number): Promise<MetricRow[]> {
  const params = new URLSearchParams({ industry, metric, year: String(year) });
  return apiGet<MetricRow[]>(`/metrics?${params.toString()}`);
}
