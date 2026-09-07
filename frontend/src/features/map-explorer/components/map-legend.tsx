"use client";

import type { MetricKey } from "@/shared/api/types";
import { METRIC_LABELS } from "../lib/map-state";
import { NO_DATA_COLOR, type MetricColorClass } from "../lib/metric-color";

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/** 범례 구간 값 표기 — 비율 지표는 %(소수 1자리, 음수 부호 그대로), 점포수는 정수. */
const FORMAT_BY_METRIC: Record<MetricKey, (value: number) => string> = {
  closure_rate: percent,
  growth_rate: percent,
  store_count: (value) => String(Math.round(value)),
};

export function formatLegendValue(metric: MetricKey, value: number): string {
  return FORMAT_BY_METRIC[metric](value);
}

interface MapLegendProps {
  metric: MetricKey;
  classes: MetricColorClass[];
}

/** 지도 우하단 단계구분도 범례 — 색 스와치 + 값 구간 텍스트 라벨 (색에만 의존하지 않는다).
 *  MapLibre 어트리뷰션(우하단 최하부) 바로 위, 좌하단은 Next dev 인디케이터와 겹쳐 피한다.
 *  데이터가 없으면(빈 classes) 렌더링하지 않는다. */
export function MapLegend({ metric, classes }: MapLegendProps) {
  if (classes.length === 0) return null;
  return (
    <div className="absolute right-3 bottom-9 z-10 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2.5 shadow-md">
      <p className="mb-1.5 text-xs font-semibold text-[var(--text-primary)]">{METRIC_LABELS[metric]}</p>
      <ul className="flex flex-col gap-1">
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
