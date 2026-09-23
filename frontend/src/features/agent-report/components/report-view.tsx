import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GradeBadge } from "@/shared/ui/grade-badge";
import type { AgentState } from "../lib/agent-events";
import styles from "./analysis-workspace.module.css";

const SECTION_ORDER = ["verdict", "market", "shock", "funding", "calculator"] as const;

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
  const sections = SECTION_ORDER.filter((s) => state.sections[s]);

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
            <span><small className="text-[var(--accent)]">01</small>상권 진단</span>
            <span><small className="text-[var(--accent)]">02</small>충격 분석</span>
            <span><small className="text-[var(--accent)]">03</small>정책자금</span>
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
          <section key={section} className={`${styles.reportSection} border-[var(--border)]`}>
            <p className={`${styles.sectionNumber} text-[var(--accent)]`} aria-hidden="true">{String(index + 1).padStart(2, "0")} / ANALYSIS</p>
            <div className={`${styles.markdown} report-markdown`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.sections[section]}</ReactMarkdown>
            </div>
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
