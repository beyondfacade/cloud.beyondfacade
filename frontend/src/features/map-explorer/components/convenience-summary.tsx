"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchConvenienceSummary } from "../api";

/** 원천 기준연월 YYYYMM → "YYYY년 M월". */
function formatStdrYm(ym: string): string {
  return `${ym.slice(0, 4)}년 ${Number(ym.slice(4, 6))}월`;
}

/** 사이드패널 편의점 한 줄 요약 — 행정동 선택 시에만 최신 스냅샷을 조회한다. */
export function ConvenienceSummarySection({ regionCode }: { regionCode: string }) {
  const summary = useQuery({
    queryKey: ["convenience-summary", regionCode],
    queryFn: () => fetchConvenienceSummary(regionCode),
  });

  return (
    <section className="mt-3 text-sm text-[var(--text-secondary)]" aria-label="편의점 현황">
      {summary.isPending && <div className="h-5 rounded bg-[var(--bg-raised)]" role="status" aria-label="불러오는 중" />}
      {summary.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          편의점 현황을 불러오지 못했습니다.
        </p>
      )}
      {summary.data && (
        <p>
          {summary.data.store_count === 0 ? "편의점이 없습니다." : `편의점 ${summary.data.store_count}곳`}
          {summary.data.source_stdr_ym && ` · 기준 ${formatStdrYm(summary.data.source_stdr_ym)}`}
        </p>
      )}
    </section>
  );
}
