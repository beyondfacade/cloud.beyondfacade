"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMetrics, fetchRegionsGeoJson } from "../api";
import type { MetricKey } from "@/shared/api/types";

/** 지도 경계(geojson)는 불변으로 간주해 staleTime Infinity, 지표 값(rows)은 파라미터 변경 시마다 재조회. */
export function useMapData(metric: MetricKey, industry: string, year: number) {
  const geojson = useQuery({
    queryKey: ["geojson"],
    queryFn: fetchRegionsGeoJson,
    staleTime: Infinity,
  });

  const rows = useQuery({
    queryKey: ["metrics", metric, industry, year],
    queryFn: () => fetchMetrics(industry, metric, year),
  });

  return { geojson, rows };
}
