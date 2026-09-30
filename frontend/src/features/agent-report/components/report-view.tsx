import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReportSection } from "@/shared/api/types";
import { GradeBadge } from "@/shared/ui/grade-badge";
import type { AgentState } from "../lib/agent-events";
import { ReportVisuals } from "./report-visuals";
import styles from "./analysis-workspace.module.css";

const SECTION_ORDER: ReportSection[] = ["verdict", "reasons", "analogs", "conditions", "alternatives", "funding"];
const SECTION_LABEL: Record<ReportSection, string> = {
  verdict: "판정",
  reasons: "왜 안 되나",
  analogs: "유사 사례",
  conditions: "그래도 한다면",
  alternatives: "대안 동네·업종",
  funding: "대안 업종 지원사업",
};

interface Citation {
  title: string;
  url: string;
  grade: "fact" | "signal";
}

function isCitation(v: unknown): v is Citation {
  const c = v as Partial<Citation> | null;
  return (
    typeof c === "object" &&
    c !== null &&
    typeof c.title === "string" &&
    typeof c.url === "string" &&
    (c.grade === "fact" || c.grade === "signal")
  );
}

interface ReportViewProps {
  state: AgentState;
}

export function ReportView({ state }: ReportViewProps) {
  const sections = SECTION_ORDER.filter((s) => state.facts || state.sections[s]);

  if (sections.length === 0) {
    return (
      <div className={`${styles.reportSheet} ${styles.emptySheet} border-[var(--border)] bg-[var(--bg-surface)]`}>
        <div className={`${styles.reportMasthead} border-[var(--border)] text-[var(--text-secondary)]`}>
          <span>NEIGHBORHOOD REPORT</span><span>상권 분석 리포트</span>
        </div>
        <div className={styles.emptyContent}>
          <span className={`${styles.emptyMark} text-[var(--accent)] bg-[var(--bg-raised)]`} aria-hidden="true">✳</span>
          <p className={`${styles.eyebrow} text-[var(--accent)]`}>A CLOSER LOOK AT YOUR NEIGHBORHOOD</p>
          <h2>우리 동네를 이해하는<br />또 하나의 시선.</h2>
          <p className={`${styles.emptyDescription} text-[var(--text-secondary)]`}>아직 리포트가 없습니다.<br />지역 코드와 업종을 확인한 뒤 분석을 시작하세요.<br />분석 내용과 참고 자료가 이곳에 차례로 모입니다.</p>
          <div className={`${styles.reportOutline} border-[var(--border)]`}>
            {SECTION_ORDER.map((section, index) => (
              <span key={section}><small className="text-[var(--accent)]">{String(index + 1).padStart(2, "0")}</small>{SECTION_LABEL[section]}</span>
            ))}
          </div>
        </div>
        <p className={`${styles.reportFooter} border-[var(--border)] text-[var(--text-secondary)]`}>METABOLE<span>동네의 맥락에서, 다음 가능성으로.</span></p>
      </div>
    );
  }

  const citations = state.citations.filter(isCitation);

  return (
    <article className={`${styles.reportSheet} border-[var(--border)] bg-[var(--bg-surface)]`} aria-label="상권 분석 리포트">
      <header className={`${styles.reportMasthead} border-[var(--border)] text-[var(--text-secondary)]`}>
        <span>NEIGHBORHOOD REPORT</span><span>{state.error ? "작성 중단" : state.done ? "작성 완료" : "리포트 작성 중"}</span>
      </header>
      <div className={styles.reportBody}>
        {sections.map((section, index) => (
          <section key={section} aria-label={SECTION_LABEL[section]} className={`${styles.reportSection} border-[var(--border)]`}>
            <p className={`${styles.sectionNumber} text-[var(--accent)]`} aria-hidden="true">{String(index + 1).padStart(2, "0")} / ANALYSIS</p>
            {state.facts && <>
              <h2 className="mb-5 text-xl font-semibold text-[var(--text-primary)]">{SECTION_LABEL[section]}</h2>
              <ReportVisuals facts={state.facts} section={section} />
            </>}
            {state.sections[section] ? <div className={`${styles.markdown} report-markdown`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.facts
                ? state.sections[section].replace(new RegExp(`^(#{1,6}\\s+)?${SECTION_LABEL[section]}\\s*(\\n|$)`), "")
                : state.sections[section]}</ReactMarkdown>
            </div> : <div role="status" aria-label="본문 작성 중" className="h-4 w-3/4 animate-pulse rounded bg-[var(--bg-raised)] motion-reduce:animate-none" />}
          </section>
        ))}
        {state.done && citations.length > 0 && (
          <div className={`${styles.citations} border-[var(--border)]`}>
            <h3>참고 자료</h3>
            <ul className="mt-3 flex flex-col divide-y divide-[var(--border)]">
              {citations.map((c) => (
                <li key={`${c.title}:${c.url}`} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="min-w-0 text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  >
                    {c.title}
                  </a>
                  <GradeBadge grade={c.grade} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </article>
  );
}
