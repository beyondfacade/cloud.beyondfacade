"use client";

import { useQuery } from "@tanstack/react-query";
import type { CategoryRow } from "@/shared/api/types";
import { fetchRegionsGeoJson } from "../api";
import { METRIC_SOURCES, type MetricQuery } from "../lib/metric-sources";

/** 경계는 불변으로 캐시하고 업종별 최신 판정을 조회한다.
 *  판정 제외 업종은 enabled=false로 조회를 생략한다. */
export function useMapData(query: MetricQuery, enabled = true) {
  const geojson = useQuery({
    queryKey: ["geojson"],
    queryFn: fetchRegionsGeoJson,
    staleTime: Infinity,
  });

  const source = METRIC_SOURCES.verdict;
  const rows = useQuery<CategoryRow[]>({
    queryKey: source.queryKey(query),
    queryFn: () => source.fetch(query),
    enabled,
  });

  return { geojson, rows, source };
}
