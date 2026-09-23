"use client";

import { useQuery } from "@tanstack/react-query";
import type { MapMetricKey } from "@/shared/api/types";
import { fetchRegionsGeoJson } from "../api";
import { METRIC_SOURCES } from "../lib/metric-sources";

/** 지도 경계(geojson)는 불변으로 간주해 staleTime Infinity, 지표 값(rows)은 파라미터 변경 시마다 재조회.
 *  지표마다 원천이 다르지만 분기하지 않는다 — METRIC_SOURCES 테이블이 질의 키와 조회 함수를 함께 준다. */
export function useMapData(metric: MapMetricKey, industry: string, year: number) {
  const geojson = useQuery({
    queryKey: ["geojson"],
    queryFn: fetchRegionsGeoJson,
    staleTime: Infinity,
  });

  const source = METRIC_SOURCES[metric];
  const rows = useQuery({
    queryKey: source.queryKey(industry, year),
    queryFn: () => source.fetch(industry, year),
  });

  return { geojson, rows };
}
