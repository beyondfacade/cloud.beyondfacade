"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { industryLabel, type IndustryId } from "@/shared/industries";
import { fetchRegionSummary } from "../api";
import { NO_CLOSURE_HISTORY_INDUSTRIES } from "../lib/map-state";
import { ConvenienceSummarySection } from "./convenience-summary";
import { CLOSED_STORE_STRATEGY } from "./marker-strategies";
import { NeighborhoodLine } from "./neighborhood-line";
import { VerdictSection } from "./verdict-section";
import styles from "./map-workspace.module.css";

interface SidePanelProps {
  regionCode: string | null;
  /** 관문에서 온 예산(원) — 리포트와 자금 계획 링크에 실어 보낸다. */
  budget?: number | null;
  industry: string;
  showClosed?: boolean;
  onToggleClosed?: (next: boolean) => void;
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

export function SidePanel({ regionCode, industry, budget = null, showClosed, onToggleClosed }: SidePanelProps) {
  const summary = useQuery({
    queryKey: ["region-summary", regionCode, industry],
    queryFn: () => fetchRegionSummary(regionCode!, industry),
    enabled: !!regionCode,
  });

  const label = industryLabel(industry);
  const params = new URLSearchParams({ region: regionCode ?? "", industry });
  if (budget !== null) params.set("budget", String(budget));

  return (
    <aside className={styles.brief} aria-label="선택한 동네의 상권 정보">
      <p className={styles.eyebrow}>DISTRICT BRIEF</p>
      {!regionCode && (
        <div className={styles.emptyBrief}>
          <span className={styles.emptyIcon} aria-hidden="true">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none"><circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="1.25" /><path d="m20.5 11.5-3 6-6 3 3-6 6-3Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" /><path d="M16 2v4m0 20v4M2 16h4m20 0h4" stroke="currentColor" strokeWidth="1.25" /></svg>
          </span>
          <h2>어느 동네가 궁금하세요?</h2>
          <span className={styles.emptyStatus}>선택된 행정동 없음</span>
          <p>
            지도에서 행정동을 클릭하면 {label} 지표와 신호가 여기에 표시됩니다.
          </p>
          <span className={styles.emptyGuide}>동네 선택 → 지표 확인 → AI 분석</span>
        </div>
      )}

      {regionCode && summary.isPending && (
        <div role="status" aria-label="불러오는 중" className={styles.loadingBrief}>
          <p className="mb-6 text-sm text-[var(--text-secondary)]">동네의 정보를 살펴보고 있어요.</p>
          <div className="mb-5 h-5 w-24 rounded bg-[var(--bg-raised)]" aria-hidden />
          <SkeletonRows />
        </div>
      )}

      {regionCode && summary.isError && (
        <div role="alert" className={styles.emptyBrief}>
          <span className={styles.emptyIcon} aria-hidden="true">—</span>
          <h2>잠시, 정보를 확인할 수 없어요.</h2>
          {/* "데이터 없음"은 스냅샷 업종 안내와 뜻이 겹친다 — 조회 실패는 실패라고 말한다 (v0.14.1) */}
          <span className="text-xs font-medium text-[var(--danger)]">불러오기 실패</span>
          <span className="text-sm leading-relaxed text-[var(--text-secondary)]">
            <span className="tabular-nums">{regionCode}</span> 행정동의 {label} 지표를 불러오지 못했습니다.
          </span>
        </div>
      )}

      {regionCode && summary.data && (
        <header className={styles.briefHeading}>
          <h2>{summary.data.name}</h2>
          <p className="text-xs text-[var(--text-secondary)]">
            <span className="tabular-nums">{summary.data.region_code}</span> · {label}
          </p>
        </header>
      )}

      {regionCode && (
        <>
          {industry === "convenience_store" ? (
            <>
              <ConvenienceSummarySection regionCode={regionCode} />
              <p className="mt-2 text-xs text-[var(--text-secondary)]">판정은 담배권 특화 신호 단계에서 제공</p>
            </>
          ) : (
            <>
              <VerdictSection regionCode={regionCode} industry={industry} />
              <NeighborhoodLine regionCode={regionCode} />
            </>
          )}
          <ClosedStoresToggle regionCode={regionCode} industry={industry} checked={showClosed ?? false} onChange={onToggleClosed ?? (() => {})} />
        </>
      )}

      {regionCode && (
        <div className={`${styles.briefCta} flex flex-col gap-2`}>
          <Link
            href={`/analysis?${params}`}
            className="block rounded-lg bg-[var(--accent)] px-4 py-3 text-center text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px"
          >
            AI 분석 리포트 보기
          </Link>
          <Link
            href={`/plan?${params}`}
            className="self-center text-xs text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            자금 계획 →
          </Link>
        </div>
      )}
    </aside>
  );
}

function ClosedStoresToggle({ regionCode, industry, checked, onChange }: {
  regionCode: string; industry: string; checked: boolean; onChange: (next: boolean) => void;
}) {
  const closed = useQuery({
    queryKey: CLOSED_STORE_STRATEGY.queryKey(regionCode, industry),
    queryFn: () => CLOSED_STORE_STRATEGY.fetch(regionCode, industry),
    enabled: checked,
  });
  // 스냅샷 원천(childcare·convenience_store)·close_date NULL(academy) 업종은 폐업 이력이 없다 —
  // 토글을 보이면 "0곳 폐업"이 거짓이 된다 (source absence ≠ zero).
  if (NO_CLOSURE_HISTORY_INDUSTRIES.has(industry as IndustryId)) {
    return null;
  }
  return (
    <div className="mt-2 flex flex-col gap-1 text-xs">
      <label className="flex items-center gap-2 text-[var(--text-secondary)]">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        최근 2년 폐업 점포 보기
      </label>
      {checked && closed.data && (
        <p className="text-[var(--text-primary)]">
          이 동에서 최근 2년 {industryLabel(industry)} <span className="tabular-nums">{closed.data.length}</span>곳 폐업
        </p>
      )}
    </div>
  );
}
