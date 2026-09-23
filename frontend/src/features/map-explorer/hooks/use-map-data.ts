"use client";

import { useQuery } from "@tanstack/react-query";
import type { CategoryRow, MapMetricKey, MetricRow } from "@/shared/api/types";
import { fetchRegionsGeoJson } from "../api";
import { METRIC_SOURCES, type MetricQuery } from "../lib/metric-sources";

/** 지도 경계(geojson)는 불변으로 간주해 staleTime Infinity, 지표 값(rows)은 파라미터 변경 시마다 재조회.
 *  지표마다 원천이 다르지만 분기하지 않는다 — METRIC_SOURCES 테이블이 질의 키와 조회 함수를 함께 준다.
 *  rows는 원천의 `kind`에 따라 숫자 행 또는 범주 행이다. 어느 쪽인지는 `source.kind`가 말한다.
 *  query 전부를 넘기고 원천이 자기 축의 값만 쓴다. */
export function useMapData(metric: MapMetricKey, query: MetricQuery) {
  const geojson = useQuery({
    queryKey: ["geojson"],
    queryFn: fetchRegionsGeoJson,
    staleTime: Infinity,
  });

  const source = METRIC_SOURCES[metric];
  const rows = useQuery<MetricRow[] | CategoryRow[]>({
    queryKey: source.queryKey(query),
    queryFn: () => source.fetch(query),
  });

  return { geojson, rows, source };
}
