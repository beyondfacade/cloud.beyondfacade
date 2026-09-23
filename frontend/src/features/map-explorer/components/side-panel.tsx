"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { GradeBadge } from "@/shared/ui/grade-badge";
import { industryLabel, type IndustryId } from "@/shared/industries";
import { fetchRegionSummary } from "../api";
import { SNAPSHOT_INDUSTRIES } from "../lib/map-state";
import { ChildcareSummarySection } from "./childcare-summary";
import { ConvenienceSummarySection } from "./convenience-summary";
import { HourGapSection } from "./hour-gap-chart";
import { NeighborhoodProfileSection } from "./neighborhood-profile";
import { StayingPowerSection } from "./staying-power";
import { TimeBlockSection } from "./time-block-bars";
import styles from "./map-workspace.module.css";

/** 전용 원천이 있는 업종의 추가 섹션 — 업종이 스스로 무엇을 보여줄지 등록한다 (조건 분기 대신 레지스트리). */
const INDUSTRY_SECTIONS: Partial<Record<IndustryId, ComponentType<{ regionCode: string }>>> = {
  childcare: ChildcareSummarySection,
  convenience_store: ConvenienceSummarySection,
};

interface SidePanelProps {
  regionCode: string | null;
  /** 관문에서 온 예산(원) — 자금 계획 링크에 실어 보낸다. */
  budget?: number | null;
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

export function SidePanel({ regionCode, industry, budget = null }: SidePanelProps) {
  const summary = useQuery({
    queryKey: ["region-summary", regionCode, industry],
    queryFn: () => fetchRegionSummary(regionCode!, industry),
    enabled: !!regionCode,
  });

  const label = industryLabel(industry);
  const IndustrySection = INDUSTRY_SECTIONS[industry as IndustryId];
  const isSnapshot = SNAPSHOT_INDUSTRIES.has(industry as IndustryId);

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
        <>
          <header className={styles.briefHeading}>
            <h2>
              {summary.data.name}
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">
              <span className="tabular-nums">{summary.data.region_code}</span> · {label}
            </p>
          </header>

          {/* 창업자의 질문 순서 — ① 어떤 동네인가 ② 하루가 어떻게 흐르나 ③ 내 업종은 언제 돈이 도나
              ④ 얼마나 버티나 ⑤ 업종 실적. 동네 맥락이 먼저, 업종 상세가 뒤 (무대 설계서 §5) */}
          <NeighborhoodProfileSection regionCode={regionCode} />
          <TimeBlockSection regionCode={regionCode} />
          <HourGapSection regionCode={regionCode} industry={industry} />
          <StayingPowerSection regionCode={regionCode} />

          <section className="mt-7 flex flex-col gap-3" aria-label="업종 실적">
            <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">{label} 실적</h3>
            <ul className={`${styles.briefMetrics} ${styles.briefMetricsInSection}`}>
              {summary.data.cards.map((card) => (
                <li key={card.label}>
                  <div className="flex min-w-0 flex-col gap-2">
                    <span className="text-xs text-[var(--text-secondary)]">{card.label}</span>
                    <span className={styles.metricValue}>
                      {card.value}
                    </span>
                  </div>
                  <GradeBadge grade={card.grade} />
                </li>
              ))}
            </ul>
            {isSnapshot && (
              <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
                폐업률·성장률은 스냅샷 원천이라 아직 값이 없을 수 있습니다. 점포수와 아래 현황을 함께
                참고하세요.
              </p>
            )}
          </section>

          {IndustrySection && <IndustrySection regionCode={regionCode} />}

          {/* 패널이 길어져 CTA가 접힌다 — 스크롤 영역 하단에 붙인다 (E2E [5/8] 재현 근거) */}
          <div className={`${styles.briefCta} flex gap-2`}>
            <Link
              href={`/plan?region=${regionCode}&industry=${industry}${budget ? `&budget=${budget}` : ""}`}
              className="block flex-1 rounded-lg border border-[var(--accent)] px-4 py-3.5 text-center text-sm font-semibold text-[var(--accent)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px"
            >
              자금 계획 →
            </Link>
            <Link
              href={`/analysis?region=${regionCode}&industry=${industry}`}
              className="block flex-1 rounded-lg bg-[var(--accent)] px-4 py-3.5 text-center text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px"
            >
              AI 분석 →
            </Link>
          </div>
        </>
      )}
    </aside>
  );
}
