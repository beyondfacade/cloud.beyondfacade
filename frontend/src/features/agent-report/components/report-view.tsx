import Link from "next/link";
import ReactMarkdown, { type Options } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { FactSection, ReportFacts } from "@/shared/api/types";
import type { AgentState } from "../lib/agent-events";
import { analogAnchors, gradedParagraphs } from "../lib/graded-paragraphs";
import { ReportVisuals } from "./report-visuals";
import styles from "./analysis-workspace.module.css";

// 본문엔 "50~299인"처럼 범위 물결표가 흔하다 — 물결표 하나짜리 취소선을 끄지 않으면 두 범위 사이가 그어진다
const REMARK_PLUGINS: Options["remarkPlugins"] = [[remarkGfm, { singleTilde: false }]];

const SECTION_ORDER: FactSection[] = ["verdict", "reasons", "analogs", "conditions", "alternatives", "funding"];
const SECTION_LABEL: Record<FactSection, string> = {
  verdict: "판정",
  reasons: "왜 안 되나",
  analogs: "유사 사례",
  conditions: "그래도 한다면",
  alternatives: "대안 동네·업종",
  funding: "대안 업종 지원사업",
};

// 섹션별 본문 모양 — 유사 사례는 근거 표기 단위 문단·문장 단위 줄로, 유형마다 사실 → 신호 순서로 다시 짠다
const SECTION_FORMAT: Partial<Record<FactSection, (markdown: string, facts: AgentState["facts"]) => string>> = {
  analogs: (markdown, facts) => gradedParagraphs(markdown, analogAnchors(facts?.analogs)),
};

/** 사실 그림이 제목을 이미 달았으면 본문 앞머리의 같은 제목 줄을 뗀다. */
function sectionBody(state: AgentState, section: FactSection): string {
  const markdown = state.sections[section] ?? "";
  return state.facts
    ? markdown.replace(new RegExp(`^(#{1,6}\\s+)?${SECTION_LABEL[section]}\\s*(\\n|$)`), "")
    : markdown;
}

interface ReportViewProps {
  state: AgentState;
}

/** 리포트를 다 읽은 뒤 갈 곳 — 지원·대출 정보, 또는 지도로 돌아가 동네·업종을 바꿔 보기. 동·업종·예산은 주소에 싣는다. */
function NextSteps({ facts }: { facts: ReportFacts }) {
  const query = new URLSearchParams({ region: facts.region.code, industry: facts.region.industry_id });
  if (facts.budget != null) query.set("budget", String(facts.budget));
  return (
    <nav aria-label="다음 단계" className="mt-10 grid gap-3 sm:grid-cols-2">
      <Link href={`/support?${query}`} className="flex flex-col gap-1 rounded-lg bg-[var(--accent)] p-4 text-[var(--accent-fg)] hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">
        <span className="text-base font-semibold">창업 지원·대출 정보 보기 →</span>
        <span className="text-xs opacity-90">정책자금·보증, 우리 구 전용 지원, 업종 관련 공고와 상담 창구</span>
      </Link>
      <Link href={`/map?${query}`} className="flex flex-col gap-1 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-[var(--text-primary)] hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">
        <span className="text-base font-semibold">← 다른 창업 알아보기</span>
        <span className="text-xs text-[var(--text-secondary)]">지도로 돌아가 동네나 업종을 바꿔 다시 비교해 보세요</span>
      </Link>
    </nav>
  );
}

export function ReportView({ state }: ReportViewProps) {
  const sections = SECTION_ORDER.filter((s) => state.facts || state.sections[s]);

  if (sections.length === 0 && !state.sections.answer_lead) {
    return (
      <div className={`${styles.reportSheet} ${styles.emptySheet} border-[var(--border)] bg-[var(--bg-surface)]`}>
        <div className={`${styles.reportMasthead} border-[var(--border)] text-[var(--text-secondary)]`}>
          <span>WARNING REPORT</span><span>창업 경고 리포트</span>
        </div>
        <div className={styles.emptyContent}>
          <span className={`${styles.emptyMark} text-[var(--accent)] bg-[var(--bg-raised)]`} aria-hidden="true">✳</span>
          <p className={`${styles.eyebrow} text-[var(--accent)]`}>BEFORE YOU SIGN</p>
          <h2>계약 전에 읽는<br />한 장.</h2>
          <p className={`${styles.emptyDescription} text-[var(--text-secondary)]`}>아직 리포트가 없습니다.<br />지역 코드와 업종을 확인한 뒤 분석을 시작하세요.<br />분석 내용과 참고 자료가 이곳에 차례로 모입니다.</p>
          <div className={`${styles.reportOutline} border-[var(--border)]`}>
            {SECTION_ORDER.map((section, index) => (
              <span key={section}><small className="text-[var(--accent)]">{String(index + 1).padStart(2, "0")}</small>{SECTION_LABEL[section]}</span>
            ))}
          </div>
        </div>
        <p className={`${styles.reportFooter} border-[var(--border)] text-[var(--text-secondary)]`}>METABOLE<span>근거가 있는 경고, 그다음의 대안.</span></p>
      </div>
    );
  }

  const citations = state.citations;

  return (
    <article className={`${styles.reportSheet} border-[var(--border)] bg-[var(--bg-surface)]`} aria-label="창업 경고 리포트">
      <header className={`${styles.reportMasthead} border-[var(--border)] text-[var(--text-secondary)]`}>
        <span>WARNING REPORT</span><span>{state.error ? "작성 중단" : state.done ? "작성 완료" : "리포트 작성 중"}</span>
      </header>
      <div className={styles.reportBody}>
        {state.sections.answer_lead ? (
          <section aria-label="질문에 대한 답" className={`${styles.reportSection} border-[var(--border)]`}>
            <h2 className="mb-2 text-xl font-semibold text-[var(--accent)]">질문에 대한 답</h2>
            <p className="mb-5 text-sm text-[var(--text-secondary)]">첫 문장과 근거는 사실에서 코드가 쓴 것이고, AI 해석은 그 이유를 풀어 쓴 것입니다.</p>
            <div className={`${styles.markdown} report-markdown`}>
              <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{state.sections.answer_lead}</ReactMarkdown>
            </div>
            <p className="mb-2 mt-5 text-sm font-semibold text-[var(--text-secondary)]">AI 해석</p>
            <div role="region" aria-label="AI 해석 본문" className="min-h-32">
              {state.sections.answer ? (
                <div className={`${styles.markdown} report-markdown`}>
                  <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{state.sections.answer}</ReactMarkdown>
                </div>
              ) : !state.done && !state.error ? (
                <div role="status" aria-label="AI 해석 작성 중" className="space-y-3 pt-1 animate-pulse motion-reduce:animate-none">
                  <div className="h-4 w-full rounded bg-[var(--bg-raised)]" />
                  <div className="h-4 w-full rounded bg-[var(--bg-raised)]" />
                  <div className="h-4 w-3/4 rounded bg-[var(--bg-raised)]" />
                </div>
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">AI 해석을 받지 못했습니다.</p>
              )}
            </div>
          </section>
        ) : state.sections.answer && (
          <section aria-label="해석" className={`${styles.reportSection} border-[var(--border)]`}>
            <h2 className="mb-2 text-xl font-semibold text-[var(--accent)]">해석</h2>
            <p className="mb-5 text-sm text-[var(--text-secondary)]">AI가 아래 사실을 읽고 쓴 해석입니다. 판정과 수치는 아래 사실을 기준으로 보세요.</p>
            <div className={`${styles.markdown} report-markdown`}>
              <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{state.sections.answer}</ReactMarkdown>
            </div>
          </section>
        )}
        {sections.map((section, index) => (
          <section key={section} aria-label={SECTION_LABEL[section]} className={`${styles.reportSection} border-[var(--border)]`}>
            <p className={`${styles.sectionNumber} text-[var(--accent)]`} aria-hidden="true">{String(index + 1).padStart(2, "0")} / ANALYSIS</p>
            {state.facts && <>
              <h2 className="mb-5 text-xl font-semibold text-[var(--text-primary)]">{SECTION_LABEL[section]}</h2>
              <ReportVisuals facts={state.facts} section={section} />
            </>}
            {state.sections[section] ? <div className={`${styles.markdown} report-markdown`}>
              <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{SECTION_FORMAT[section]?.(sectionBody(state, section), state.facts) ?? sectionBody(state, section)}</ReactMarkdown>
            </div> : <div role="status" aria-label="본문 작성 중" className="h-4 w-3/4 animate-pulse rounded bg-[var(--bg-raised)] motion-reduce:animate-none" />}
          </section>
        ))}
        {state.done && citations.length > 0 && (
          <div className={`${styles.citations} border-[var(--border)]`}>
            <h3>최근 뉴스 — 네이버 검색결과</h3>
            <ul className="mt-3 flex flex-col divide-y divide-[var(--border)]">
              {citations.map((c) => (
                <li key={`${c.title}:${c.url}`} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 py-2.5 text-sm">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="min-w-0 text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  >
                    {c.title}
                  </a>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {c.press ?? new URL(c.url).hostname.replace(/^www\./, "")}
                    {c.published_at && <> · <time dateTime={c.published_at}>{c.published_at}</time></>}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-[var(--text-secondary)]">네이버 뉴스 검색 결과입니다. 기사 내용은 원문에서 확인하세요.</p>
          </div>
        )}
        {state.done && state.facts?.region && <NextSteps facts={state.facts} />}
      </div>
    </article>
  );
}
