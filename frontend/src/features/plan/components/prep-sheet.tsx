"use client";

import { useState } from "react";
import { buildPrepMarkdown, buildQuestionsMarkdown, type PrepContext } from "../lib/prep-markdown";

/** 준비자료 한 화면 — 계획·비교·후보·질문·단서를 모아 Markdown으로 내보낸다.
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
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">상담 준비자료</h3>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">복사하거나 인쇄해 상담에 들고 가세요.</p>
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
          <button type="button" onClick={() => window.print()}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-xs text-[var(--text-primary)]">인쇄</button>
        </div>
      </div>
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-xs leading-relaxed text-[var(--text-primary)]"
        data-prep-markdown>{markdown}</pre>
    </section>
  );
}
