"use client";

import { useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { industryLabel } from "@/shared/industries";
import { fetchAnalysisRegionSummary } from "../api";
import { AnalysisForm } from "./analysis-form";
import { ProgressPanel } from "./progress-panel";
import { ReportView } from "./report-view";
import { useAgentReport } from "../hooks/use-agent-report";
import styles from "./analysis-workspace.module.css";

/** URL의 동·업종이 있으면 즉시 분석하고, 직접 방문이면 입력 폼을 제공한다. */
export function AnalysisPage() {
  const searchParams = useSearchParams();
  const region = searchParams.get("region") ?? "";
  const industry = searchParams.get("industry") ?? "";
  const rawBudget = searchParams.get("budget");
  const parsedBudget = rawBudget?.trim() ? Number(rawBudget) : NaN;
  const budget = Number.isSafeInteger(parsedBudget) && parsedBudget >= 0 ? parsedBudget : undefined;

  return <AnalysisWorkspace key={JSON.stringify([region, industry, budget])} region={region} industry={industry} budget={budget} />;
}

function AnalysisWorkspace({ region, industry, budget }: { region: string; industry: string; budget?: number }) {
  const { state, start, loading } = useAgentReport();
  const autoStart = !!region && !!industry;
  const started = useRef(false);
  const summary = useQuery({
    queryKey: ["region-summary", region, industry],
    queryFn: () => fetchAnalysisRegionSummary(region, industry),
    enabled: autoStart,
  });

  useEffect(() => {
    if (!autoStart || started.current) return;
    started.current = true;
    void start({ region, industry, ...(budget === undefined ? {} : { budget }) });
  }, [autoStart, region, industry, budget, start]);

  return (
    <main className={styles.workspace}>
      <header className={styles.pageHeader}>
        <div>
          <p className={`${styles.eyebrow} text-[var(--accent)]`}>SEOUL COMMERCIAL METABOLE / ANALYSIS</p>
          <h1>판정의 근거를,<br className={styles.mobileBreak} /> 한 장으로.</h1>
          <p className={`${styles.pageDescription} text-[var(--text-secondary)]`}>동네와 업종을 정하면 판정 근거, 그래도 한다면 지킬 조건, 대안을 차례로 정리합니다.</p>
        </div>
        <span className={`${styles.pageEdition} text-[var(--text-secondary)]`}>창업 경고 리포트<span aria-hidden="true">↘</span></span>
      </header>
      <div className={styles.workspaceGrid}>
        <aside className={styles.sidebar} aria-label="분석 설정과 진행 상황">
          <section className={`${styles.contextPanel} border-[var(--border)] bg-[var(--bg-surface)]`} aria-labelledby="analysis-context-title">
            <div className={styles.panelHeading}>
              <span className={`${styles.panelNumber} text-[var(--accent)]`}>01</span>
              <h2 id="analysis-context-title">분석할 상권</h2>
            </div>
            {autoStart ? (
              <form className={`${styles.form} mt-4`} onSubmit={(event) => {
                event.preventDefault();
                const question = String(new FormData(event.currentTarget).get("question") ?? "").trim();
                void start({ region, industry, ...(budget === undefined ? {} : { budget }), ...(question ? { question } : {}) });
              }}>
                <p className="text-sm text-[var(--text-primary)]">
                  {summary.data?.name ?? region} · {industryLabel(industry)}{budget === undefined ? "" : ` · 예산 ${(budget / 10_000).toLocaleString("ko-KR", { maximumFractionDigits: 4 })}만원`}
                </p>
                <details>
                  <summary className="cursor-pointer text-xs text-[var(--text-secondary)]">추가 질문 (선택)</summary>
                  <label className="mt-3 flex flex-col gap-1.5 text-xs text-[var(--text-secondary)]">
                    추가 질문
                    <textarea name="question" rows={3} className={`${styles.field} resize-y border border-[var(--border)] bg-[var(--bg-base)] text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]`} />
                  </label>
                </details>
                <button type="submit" disabled={loading} className={`${styles.submitButton} bg-[var(--accent)] text-[var(--accent-fg)] hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:pointer-events-none disabled:opacity-50`}>
                  다시 분석
                </button>
              </form>
            ) : (
              <>
                <p className={`${styles.panelDescription} text-[var(--text-secondary)]`}>지도에서 고른 동네를 이어서 살펴보거나,<br />지역 코드와 업종을 직접 입력하세요.</p>
                <AnalysisForm initialRegion={region} initialIndustry={industry} onSubmit={start} disabled={loading} />
              </>
            )}
            {state.error && (
              <p role="alert" className={`${styles.error} text-[var(--danger)]`}>
                {state.error}
              </p>
            )}
          </section>
          <ProgressPanel state={state} />
        </aside>
        <div className={styles.reportColumn}>
          <ReportView state={state} />
        </div>
      </div>
    </main>
  );
}
