"use client";

import { availableFact } from "../../lib/available-fact";
import type { UnavailableFact, RegionCommerceChangeDetail } from "@/shared/api/types";

/** 상권변화 코드 → 배지 색 토큰. 이름은 원천 `change_name`을 그대로 쓴다 (조건 분기 대신 테이블). */
const BADGE_TOKEN: Record<string, string> = {
  LL: "var(--accent)", // 다이나믹
  LH: "var(--ok)", // 상권확장
  HH: "var(--text-secondary)", // 정체
  HL: "var(--danger)", // 상권축소
};

function months(value: number | null): string {
  return value == null ? "집계 없음" : `${Math.round(value)}개월`;
}

function Row({ label, value, seoul }: { label: string; value: number | null; seoul: number | null | undefined }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-2 text-sm">
      <span className="text-[var(--text-secondary)]">{label}</span>
      <span className="text-right">
        <span className="tabular-nums text-[var(--text-primary)]">{months(value)}</span>
        {seoul !== undefined && seoul !== null && (
          <span className="ml-1.5 text-xs tabular-nums text-[var(--text-secondary)]">· 서울 {Math.round(seoul)}</span>
        )}
      </span>
    </li>
  );
}

export function StayingPowerBody({ detail }: { detail: RegionCommerceChangeDetail }) {
  const code = detail.change_code ?? "";
  return (
    <>
      {detail.change_name && (
        <span
          className="inline-flex w-fit items-center rounded border px-2 py-0.5 text-xs font-medium"
          style={{ borderColor: BADGE_TOKEN[code] ?? "var(--border)", color: BADGE_TOKEN[code] ?? "var(--text-secondary)" }}
          data-change-code={code}
        >
          {detail.change_name}
        </span>
      )}
      <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]" aria-label="영업 지속 개월">
        <Row label="영업 중인 가게 평균" value={detail.operating_months} seoul={detail.seoul?.operating_months} />
        <Row label="폐업까지 버틴 개월" value={detail.closed_months} seoul={detail.seoul?.closed_months} />
      </ul>
      <p className="text-xs tabular-nums text-[var(--text-secondary)]">
        기준 {(detail.year_quarter ?? "").slice(0, 4)}년 {(detail.year_quarter ?? "").slice(4)}분기 · 업종 구분 없는 동 전체
      </p>
    </>
  );
}

export function StayingPower({ commerceChange }: { commerceChange?: RegionCommerceChangeDetail | UnavailableFact }) {
  const data = availableFact(commerceChange);
  if (!data) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  return (
    <section className="flex flex-col gap-3" aria-label="얼마나 버티나">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">얼마나 버티나</h3>
      <StayingPowerBody detail={data} />
    </section>
  );
}
