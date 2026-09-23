"use client";

import { useSearchParams } from "next/navigation";
import { AnalysisForm } from "./analysis-form";
import { ProgressPanel } from "./progress-panel";
import { ReportView } from "./report-view";
import { useAgentReport } from "../hooks/use-agent-report";
import styles from "./analysis-workspace.module.css";

/** URL region·industry 프리필 → 분석 시작 → 진행 패널(좌) + 리포트(우). */
export function AnalysisPage() {
  const searchParams = useSearchParams();
  const { state, start, loading } = useAgentReport();

  return (
    <main className={styles.workspace}>
      <header className={styles.pageHeader}>
        <div>
          <p className={`${styles.eyebrow} text-[var(--accent)]`}>SEOUL COMMERCIAL ATLAS / ANALYSIS</p>
          <h1>동네의 가능성을,<br className={styles.mobileBreak} /> 한 장의 분석으로.</h1>
          <p className={`${styles.pageDescription} text-[var(--text-secondary)]`}>궁금한 지역과 업종을 정하고, 상권을 이해할 다음 단서를 찾아보세요.</p>
        </div>
        <span className={`${styles.pageEdition} text-[var(--text-secondary)]`}>AI 분석 워크스페이스<span aria-hidden="true">↘</span></span>
      </header>
      <div className={styles.workspaceGrid}>
        <aside className={styles.sidebar} aria-label="분석 설정과 진행 상황">
          <section className={`${styles.contextPanel} border-[var(--border)] bg-[var(--bg-surface)]`} aria-labelledby="analysis-context-title">
            <div className={styles.panelHeading}>
              <span className={`${styles.panelNumber} text-[var(--accent)]`}>01</span>
              <h2 id="analysis-context-title">분석할 상권</h2>
            </div>
            <p className={`${styles.panelDescription} text-[var(--text-secondary)]`}>지도에서 고른 동네를 이어서 살펴보거나,<br />지역 코드와 업종을 직접 입력하세요.</p>
            <AnalysisForm
              initialRegion={searchParams.get("region") ?? ""}
              initialIndustry={searchParams.get("industry") ?? ""}
              onSubmit={start}
              disabled={loading}
            />
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
