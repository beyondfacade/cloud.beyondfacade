"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { GradeBadge } from "@/shared/ui/grade-badge";
import { industryLabel } from "@/shared/industries";
import { fetchRegionSummary } from "../api";

interface SidePanelProps {
  regionCode: string | null;
  industry: string;
}

function SkeletonRows() {
  return (
    <div className="flex flex-col gap-4" aria-hidden>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="h-3 w-14 rounded bg-[var(--bg-raised)]" />
          <div className="h-4 w-28 rounded bg-[var(--bg-raised)]" />
        </div>
      ))}
    </div>
  );
}

export function SidePanel({ regionCode, industry }: SidePanelProps) {
  const summary = useQuery({
    queryKey: ["region-summary", regionCode, industry],
    queryFn: () => fetchRegionSummary(regionCode!, industry),
    enabled: !!regionCode,
  });

  const label = industryLabel(industry);

  return (
    <aside className="flex w-80 shrink-0 flex-col overflow-y-auto border-l border-[var(--border)] bg-[var(--bg-surface)] p-5">
      {!regionCode && (
        <div className="my-auto flex flex-col items-center gap-2 px-4 text-center">
          <span className="text-sm font-medium text-[var(--text-primary)]">선택된 행정동 없음</span>
          <span className="text-sm leading-relaxed text-[var(--text-secondary)]">
            지도에서 행정동을 클릭하면 {label} 지표와 신호가 여기에 표시됩니다.
          </span>
        </div>
      )}

      {regionCode && summary.isPending && (
        <div role="status" aria-label="불러오는 중">
          <div className="mb-5 h-5 w-24 rounded bg-[var(--bg-raised)]" aria-hidden />
          <SkeletonRows />
        </div>
      )}

      {regionCode && summary.isError && (
        <div role="alert" className="my-auto flex flex-col items-center gap-2 px-4 text-center">
          <span className="text-sm font-medium text-[var(--danger)]">데이터 없음</span>
          <span className="text-sm leading-relaxed text-[var(--text-secondary)]">
            <span className="tabular-nums">{regionCode}</span> 행정동의 {label} 지표를 불러오지 못했습니다.
          </span>
        </div>
      )}

      {regionCode && summary.data && (
        <>
          <header className="flex flex-col gap-0.5">
            <h2 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
              {summary.data.name}
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">
              <span className="tabular-nums">{summary.data.region_code}</span> · {label}
            </p>
          </header>

          <ul className="mt-5 flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {summary.data.cards.map((card) => (
              <li key={card.label} className="flex items-start justify-between gap-3 py-3">
                <div className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-xs text-[var(--text-secondary)]">{card.label}</span>
                  <span className="text-sm leading-snug tabular-nums text-[var(--text-primary)]">
                    {card.value}
                  </span>
                </div>
                <GradeBadge grade={card.grade} />
              </li>
            ))}
          </ul>

          <Link
            href={`/analysis?region=${regionCode}&industry=${industry}`}
            className="mt-6 rounded-md bg-[var(--accent)] px-3 py-2.5 text-center text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px"
          >
            AI 분석 →
          </Link>
        </>
      )}
    </aside>
  );
}
