"use client";

import { useState } from "react";
import ReactMarkdown, { type Options } from "react-markdown";
import remarkGfm from "remark-gfm";
import { saveAsPdf } from "@/shared/lib/save-as-pdf";
import { buildPrepMarkdown, buildQuestionsMarkdown, type PrepContext } from "../lib/prep-markdown";
import styles from "./plan-workspace.module.css";

// 금액 범위의 물결표가 취소선으로 읽히지 않게 한다
const REMARK_PLUGINS: Options["remarkPlugins"] = [[remarkGfm, { singleTilde: false }]];

/** 준비자료 한 화면 — 계획·비교·후보·질문·단서를 모아 문서로 보여 주고 Markdown 복사·PDF 저장으로 내보낸다.
 *  저장은 사용자 몫이다. **은행 전송·예약·신청은 하지 않으며 그렇게 보이는 버튼도 두지 않는다.** */
export function PrepSheet(ctx: PrepContext) {
  const [copied, setCopied] = useState<"none" | "all" | "questions">("none");
  const markdown = buildPrepMarkdown(ctx);

  async function copy(text: string, which: "all" | "questions") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(which);
    } catch {
      setCopied("none"); // 클립보드를 막은 환경 — 아래 본문을 직접 선택해 복사하면 된다
    }
  }

  if (!markdown) {
    return <p className="text-sm text-[var(--text-secondary)]">상담할 안을 고르면 준비자료가 만들어집니다.</p>;
  }

  return (
    <section className="flex flex-col gap-3" aria-label="상담 준비자료">
      <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">상담 준비자료</h3>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">복사하거나 PDF로 저장해 상담에 들고 가세요.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => copy(markdown, "all")}
            className="rounded-md bg-[var(--accent)] px-3 py-2 text-xs font-semibold text-[var(--accent-fg)]">
            {copied === "all" ? "복사했습니다" : "Markdown 복사"}
          </button>
          <button type="button" onClick={() => copy(buildQuestionsMarkdown(ctx.draft.questions), "questions")}
            disabled={ctx.draft.questions.length === 0}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-xs text-[var(--text-primary)] disabled:opacity-40">
            {copied === "questions" ? "복사했습니다" : "질문만 복사"}
          </button>
          <button type="button" onClick={() => saveAsPdf(`창업자금 상담 준비자료_${ctx.regionName}_${ctx.industryLabel}`)}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-xs text-[var(--text-primary)]">PDF로 저장</button>
        </div>
      </div>
      <div className={`${styles.prepDoc} report-markdown max-h-96 overflow-auto rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-sm text-[var(--text-primary)] print:max-h-none print:overflow-visible print:border-0 print:p-0`}
        data-prep-markdown>
        <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{markdown}</ReactMarkdown>
      </div>
    </section>
  );
}
