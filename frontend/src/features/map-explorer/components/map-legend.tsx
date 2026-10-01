"use client";

import { METRIC_SOURCES } from "../lib/metric-sources";
import { NO_DATA_COLOR, type CategoryColorClass } from "../lib/metric-color";

interface MapLegendProps {
  scale: { classes: CategoryColorClass[] };
}

/** 판정 이름과 설명을 색상과 함께 표시한다. */
function CategoryRows({ classes, labelOf }: { classes: CategoryColorClass[]; labelOf: (code: string) => { name: string; qualifier: string } }) {
  return (
    <>
      {classes.map(({ color, code }) => {
        const label = labelOf(code);
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

/** 지도 우하단 단계구분도 범례 — 색 스와치 + 판정 이름 텍스트 라벨 (색에만 의존하지 않는다).
 *  MapLibre 어트리뷰션(우하단 최하부) 바로 위, 좌하단은 Next dev 인디케이터와 겹쳐 피한다.
 *  데이터가 없으면(빈 classes) 렌더링하지 않는다. */
export function MapLegend({ scale }: MapLegendProps) {
  const source = METRIC_SOURCES.verdict;
  if (scale.classes.length === 0) return null;
  return (
    <div className="absolute right-4 bottom-10 z-10 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
      <p className="text-xs font-semibold text-[var(--text-primary)]">창업 경고</p>
      <ul className="mt-2.5 flex flex-col gap-2">
        <CategoryRows classes={scale.classes} labelOf={source.labelOf} />
        <li className="flex items-center gap-2 text-[11px] leading-none text-[var(--text-secondary)]">
          <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: NO_DATA_COLOR }} />
          데이터 없음
        </li>
      </ul>
      <p className="mt-2.5 text-[11px] leading-none text-[var(--text-secondary)]">&quot;경고 없음&quot;은 추천이 아닙니다.</p>
    </div>
  );
}
