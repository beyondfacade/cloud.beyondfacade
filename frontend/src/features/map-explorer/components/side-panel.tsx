"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { GradeBadge } from "@/shared/ui/grade-badge";
import { fetchRegionSummary } from "../api";

interface SidePanelProps {
  regionCode: string | null;
  industry: string;
}

export function SidePanel({ regionCode, industry }: SidePanelProps) {
  const summary = useQuery({
    queryKey: ["region-summary", regionCode, industry],
    queryFn: () => fetchRegionSummary(regionCode!, industry),
    enabled: !!regionCode,
  });

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-[var(--border)] bg-[var(--bg-surface)] p-4">
      {!regionCode && (
        <p className="text-sm text-[var(--text-secondary)]">지도에서 행정동을 선택하세요</p>
      )}
      {regionCode && summary.isPending && (
        <p className="text-sm text-[var(--text-secondary)]">불러오는 중...</p>
      )}
      {regionCode && summary.isError && (
        <p className="text-sm text-[var(--text-secondary)]">데이터 없음</p>
      )}
      {regionCode && summary.data && (
        <>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">{summary.data.name}</h2>
          <ul className="mt-4 flex flex-col gap-3">
            {summary.data.cards.map((card) => (
              <li key={card.label} className="flex items-center justify-between gap-2">
                <div className="flex flex-col">
                  <span className="text-xs text-[var(--text-secondary)]">{card.label}</span>
                  <span className="tabular-nums text-sm text-[var(--text-primary)]">{card.value}</span>
                </div>
                <GradeBadge grade={card.grade} />
              </li>
            ))}
          </ul>
          <Link
            href={`/analysis?region=${regionCode}&industry=${industry}`}
            className="mt-6 rounded bg-[var(--accent)] px-3 py-2 text-center text-sm font-medium text-[var(--accent-fg)]"
          >
            AI 분석 →
          </Link>
        </>
      )}
    </aside>
  );
}
