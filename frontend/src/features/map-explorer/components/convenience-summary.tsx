"use client";

import { useQuery } from "@tanstack/react-query";
import type { ConvenienceRegionSummary } from "@/shared/api/types";
import { fetchConvenienceSummary } from "../api";

/** 원천 기준연월 YYYYMM → "YYYY년 M월". */
function formatStdrYm(ym: string): string {
  return `${ym.slice(0, 4)}년 ${Number(ym.slice(4, 6))}월`;
}

export function ConvenienceSummaryList({ summary }: { summary: ConvenienceRegionSummary }) {
  if (summary.store_count === 0) {
    return <p className="text-sm text-[var(--text-secondary)]">편의점이 없습니다.</p>;
  }
  return (
    <>
      <div className="flex flex-col gap-0.5 border-t border-[var(--border)] py-3">
        <span className="text-xs text-[var(--text-secondary)]">편의점 수</span>
        <span className="py-1 text-xl font-medium tracking-tight tabular-nums text-[var(--text-primary)]">{summary.store_count}곳</span>
      </div>
      <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]" aria-label="브랜드별 점포 수">
        {summary.brands.map((row) => (
          <li key={row.brand ?? "기타"} className="flex items-center justify-between py-2 text-sm">
            <span className="text-[var(--text-primary)]">{row.brand ?? "기타"}</span>
            <span className="tabular-nums text-[var(--text-secondary)]">{row.count}곳</span>
          </li>
        ))}
      </ul>
      {summary.source_stdr_ym && (
        <p className="mt-2 text-xs tabular-nums text-[var(--text-secondary)]">
          기준 {formatStdrYm(summary.source_stdr_ym)}
        </p>
      )}
    </>
  );
}

/** 사이드패널 편의점 섹션 — 소진공 상가정보 현행 스냅샷의 브랜드 분포 (행정동 선택 시에만 조회). */
export function ConvenienceSummarySection({ regionCode }: { regionCode: string }) {
  const summary = useQuery({
    queryKey: ["convenience-summary", regionCode],
    queryFn: () => fetchConvenienceSummary(regionCode),
  });

  return (
    <section className="mt-7 flex flex-col gap-3" aria-label="편의점 현황">
      <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">편의점 현황</h3>
      {summary.isPending && <div className="h-24 rounded bg-[var(--bg-raised)]" role="status" aria-label="불러오는 중" />}
      {summary.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          편의점 현황을 불러오지 못했습니다.
        </p>
      )}
      {summary.data && <ConvenienceSummaryList summary={summary.data} />}
    </section>
  );
}
