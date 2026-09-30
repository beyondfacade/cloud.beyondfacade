"use client";

import { useState } from "react";

/** 폴링 스냅샷마다 값을 하나씩 쌓는다(최대 limit개). 서버 이력이 아니라 이 화면을 연 뒤의 세션 이력이다.
 *  stamp(dataUpdatedAt)가 바뀔 때만 추가 — 렌더 중 상태 조정 패턴이라 effect가 필요 없다. */
export function useSessionSeries(values: number[] | undefined, stamp: number, limit = 30): number[][] {
  const [state, setState] = useState<{ stamp: number; series: number[][] }>({ stamp: 0, series: [] });
  if (values && stamp && stamp !== state.stamp) {
    const series = values.map((value, i) => [...(state.series[i] ?? []), value].slice(-limit));
    setState({ stamp, series });
    return series;
  }
  return state.series;
}
