"use client";

import type { MapMetricKey } from "@/shared/api/types";
import { METRIC_LABELS } from "../lib/map-state";
import { NO_DATA_COLOR, type MetricColorClass } from "../lib/metric-color";

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/** 범례 구간 값 표기 — 비율 지표는 %(소수 1자리, 음수 부호 그대로), 점포수·개월은 정수. */
const FORMAT_BY_METRIC: Record<MapMetricKey, (value: number) => string> = {
  closure_rate: percent,
  growth_rate: percent,
  store_count: (value) => String(Math.round(value)),
  operating_months: (value) => `${Math.round(value)}개월`,
};

/** 지표 이름만으로 오해가 생기는 경우에만 붙이는 단서. 업종을 바꿔도 색이 안 변하는 이유를 말해준다. */
const NOTE_BY_METRIC: Partial<Record<MapMetricKey, string>> = {
  operating_months: "업종 구분 없는 동 전체 평균",
};

export function formatLegendValue(metric: MapMetricKey, value: number): string {
  return FORMAT_BY_METRIC[metric](value);
}

interface MapLegendProps {
  metric: MapMetricKey;
  classes: MetricColorClass[];
}

/** 지도 우하단 단계구분도 범례 — 색 스와치 + 값 구간 텍스트 라벨 (색에만 의존하지 않는다).
 *  MapLibre 어트리뷰션(우하단 최하부) 바로 위, 좌하단은 Next dev 인디케이터와 겹쳐 피한다.
 *  데이터가 없으면(빈 classes) 렌더링하지 않는다. */
export function MapLegend({ metric, classes }: MapLegendProps) {
  if (classes.length === 0) return null;
  return (
    <div className="absolute right-4 bottom-10 z-10 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
      <p className="text-xs font-semibold text-[var(--text-primary)]">{METRIC_LABELS[metric]}</p>
      {NOTE_BY_METRIC[metric] && (
        <p className="mt-0.5 text-[10px] text-[var(--text-secondary)]">{NOTE_BY_METRIC[metric]}</p>
      )}
      <ul className="mt-2.5 flex flex-col gap-2">
        {classes.map(({ color, from, to }) => (
          <li key={color} className="flex items-center gap-2 text-[11px] leading-none tabular-nums text-[var(--text-secondary)]">
            <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: color }} />
            {formatLegendValue(metric, from)} ~ {formatLegendValue(metric, to)}
          </li>
        ))}
        <li className="flex items-center gap-2 text-[11px] leading-none text-[var(--text-secondary)]">
          <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: NO_DATA_COLOR }} />
          데이터 없음
        </li>
      </ul>
    </div>
  );
}
