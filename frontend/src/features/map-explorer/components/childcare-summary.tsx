"use client";

import { useQuery } from "@tanstack/react-query";
import type { ChildcareRegionSummary } from "@/shared/api/types";
import { fetchChildcareSummary } from "../api";
import { formatOccupancy, formatWaiting } from "../lib/childcare-format";

interface Row {
  label: string;
  value: string;
  detail?: string;
}

function rowsOf(summary: ChildcareRegionSummary): Row[] {
  return [
    { label: "운영 시설", value: `${summary.center_count}곳` },
    {
      label: "가동률",
      value: formatOccupancy(summary.occupancy_rate),
      detail: `현원 ${summary.child_count.toLocaleString("ko-KR")} / 정원 ${summary.capacity.toLocaleString("ko-KR")}`,
    },
    { label: "입소대기", value: formatWaiting(summary.waiting_count), detail: "시설별 신청 합계 (중복 신청 포함)" },
  ];
}

export function ChildcareSummaryList({ summary }: { summary: ChildcareRegionSummary }) {
  if (summary.center_count === 0) {
    return <p className="text-sm text-[var(--text-secondary)]">운영 중인 어린이집이 없습니다.</p>;
  }
  return (
    <>
      <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
        {rowsOf(summary).map((row) => (
          <li key={row.label} className="flex flex-col gap-0.5 py-3">
            <span className="text-xs text-[var(--text-secondary)]">{row.label}</span>
            <span className="text-sm tabular-nums text-[var(--text-primary)]">{row.value}</span>
            {row.detail && <span className="text-xs tabular-nums text-[var(--text-secondary)]">{row.detail}</span>}
          </li>
        ))}
      </ul>
      {summary.base_date && (
        <p className="mt-2 text-xs tabular-nums text-[var(--text-secondary)]">기준일 {summary.base_date}</p>
      )}
    </>
  );
}

/** 사이드패널 어린이집 섹션 — 어린이집정보공개포털 정원·현원·대기 (행정동 선택 시에만 조회). */
export function ChildcareSummarySection({ regionCode }: { regionCode: string }) {
  const summary = useQuery({
    queryKey: ["childcare-summary", regionCode],
    queryFn: () => fetchChildcareSummary(regionCode),
  });

  return (
    <section className="mt-6 flex flex-col gap-2" aria-label="어린이집 현황">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">어린이집 현황</h3>
      {summary.isPending && <div className="h-24 rounded bg-[var(--bg-raised)]" role="status" aria-label="불러오는 중" />}
      {summary.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          어린이집 현황을 불러오지 못했습니다.
        </p>
      )}
      {summary.data && <ChildcareSummaryList summary={summary.data} />}
    </section>
  );
}
