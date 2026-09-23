"use client";

import type { MapMetricKey, NumericMetricKey } from "@/shared/api/types";
import { neighborhoodTypeLabel } from "@/shared/neighborhood";
import { METRIC_LABELS } from "../lib/map-state";
import {
  NO_DATA_COLOR,
  type CategoryColorClass,
  type MetricColorClass,
} from "../lib/metric-color";

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/** 범례 구간 값 표기 — 비율 지표는 %(소수 1자리, 음수 부호 그대로), 점포수·개월은 정수,
 *  심야 체류는 소수 2자리(1.00 = 하루 평균). 숫자 지표만이다. */
const FORMAT_BY_METRIC: Record<NumericMetricKey, (value: number) => string> = {
  closure_rate: percent,
  growth_rate: percent,
  store_count: (value) => String(Math.round(value)),
  operating_months: (value) => `${Math.round(value)}개월`,
  night_index: (value) => value.toFixed(2),
  fnb_share: percent,
};

/** 값의 기준을 한 줄로 — 심야 체류 지수는 숫자만으로 뜻이 안 선다. "업종 무관" 단서는 두지 않는다:
 *  컨트롤바의 동네/업종 무리 구조가 그 뜻을 말한다(v0.20.0). */
const UNIT_HINT: Partial<Record<MapMetricKey, string>> = {
  night_index: "1.00 = 하루 평균",
};

export function formatLegendValue(metric: NumericMetricKey, value: number): string {
  return FORMAT_BY_METRIC[metric](value);
}

/** 범례가 받는 스케일 — 숫자는 값 구간, 범주는 코드 키. 지도의 colorOf와 같은 객체에서 온다. */
export type LegendScale =
  | { kind: "numeric"; classes: MetricColorClass[] }
  | { kind: "categorical"; classes: CategoryColorClass[] };

interface MapLegendProps {
  metric: MapMetricKey;
  scale: LegendScale;
}

function NumericRows({ metric, classes }: { metric: NumericMetricKey; classes: MetricColorClass[] }) {
  return (
    <>
      {classes.map(({ color, from, to }) => (
        <li key={color} className="flex items-center gap-2 text-[11px] leading-none tabular-nums text-[var(--text-secondary)]">
          <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: color }} />
          {formatLegendValue(metric, from)} ~ {formatLegendValue(metric, to)}
        </li>
      ))}
    </>
  );
}

/** 범주 범례는 구간이 아니라 키다 — 이름 + 괄호 설명. 6종은 색만으로 못 가르므로 이 목록이 필수다. */
function CategoryRows({ classes }: { classes: CategoryColorClass[] }) {
  return (
    <>
      {classes.map(({ color, code }) => {
        const label = neighborhoodTypeLabel(code);
        return (
          <li key={code} className="flex items-center gap-2 text-[11px] leading-none text-[var(--text-secondary)]">
            <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: color }} />
            <span className="text-[var(--text-primary)]">{label.name}</span>
            <span>({label.qualifier})</span>
          </li>
        );
      })}
    </>
  );
}

/** 지도 우하단 단계구분도 범례 — 색 스와치 + 값 구간(또는 유형 이름) 텍스트 라벨 (색에만 의존하지 않는다).
 *  MapLibre 어트리뷰션(우하단 최하부) 바로 위, 좌하단은 Next dev 인디케이터와 겹쳐 피한다.
 *  데이터가 없으면(빈 classes) 렌더링하지 않는다. */
export function MapLegend({ metric, scale }: MapLegendProps) {
  if (scale.classes.length === 0) return null;
  return (
    <div className="absolute right-4 bottom-10 z-10 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
      <p className="text-xs font-semibold text-[var(--text-primary)]">{METRIC_LABELS[metric]}</p>
      {UNIT_HINT[metric] && (
        <p className="mt-0.5 text-[10px] text-[var(--text-secondary)]">{UNIT_HINT[metric]}</p>
      )}
      <ul className="mt-2.5 flex flex-col gap-2">
        {scale.kind === "categorical" ? (
          <CategoryRows classes={scale.classes} />
        ) : (
          <NumericRows metric={metric as NumericMetricKey} classes={scale.classes} />
        )}
        <li className="flex items-center gap-2 text-[11px] leading-none text-[var(--text-secondary)]">
          <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: NO_DATA_COLOR }} />
          데이터 없음
        </li>
      </ul>
    </div>
  );
}
