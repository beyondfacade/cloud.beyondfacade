"use client";

import { useState } from "react";
import type { PlanQuestion, PlanQuestionKind } from "@/shared/api/types";

/** 확인할 질문 — **서버가 주는 것은 초안이다.** 사용자가 고치고 지우고 더한다.
 *  편집본이 정본이라 다시 조회해도 덮지 않는다(plan-draft가 보관). */

const KIND_LABELS: Record<PlanQuestionKind, string> = {
  gap: "조달",
  assumption: "가정",
  procedure: "절차",
};

const FIELD =
  "w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]";

interface QuestionListProps {
  questions: PlanQuestion[];
  onChange: (questions: PlanQuestion[]) => void;
  isPending?: boolean;
  isError?: boolean;
}

export function QuestionList({ questions, onChange, isPending, isError }: QuestionListProps) {
  const [draftText, setDraftText] = useState("");

  const replace = (index: number, text: string) =>
    onChange(questions.map((q, i) => (i === index ? { ...q, text } : q)));
  const remove = (index: number) => onChange(questions.filter((_, i) => i !== index));
  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= questions.length) return;
    const next = [...questions];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  const add = () => {
    const text = draftText.trim();
    if (!text) return;
    onChange([...questions, { text, basis: "직접 추가", kind: "procedure" }]);
    setDraftText("");
  };

  return (
    <section className="flex flex-col gap-3" aria-label="상담에서 확인할 것">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">상담에서 확인할 것</h3>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          계산에서 뽑은 초안입니다. 고치고 지우고 더하세요 — 상담 준비자료에 이대로 실립니다.
        </p>
      </div>

      {isPending && <div role="status" aria-label="불러오는 중" className="h-20 rounded bg-[var(--bg-raised)]" />}
      {isError && <p role="alert" className="text-sm text-[var(--danger)]">질문 초안을 불러오지 못했습니다. 직접 적어도 됩니다.</p>}

      <ol className="flex flex-col gap-2">
        {questions.map((q, index) => (
          <li key={`${index}-${q.basis}`} className="rounded-lg border border-[var(--border)] p-3">
            <div className="flex items-start gap-2">
              <span className="mt-1 shrink-0 rounded bg-[var(--bg-raised)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]">
                {KIND_LABELS[q.kind] ?? q.kind}
              </span>
              <label className="flex-1">
                <span className="sr-only">질문 {index + 1}</span>
                <textarea value={q.text} rows={2} onChange={(e) => replace(index, e.target.value)}
                  aria-label={`질문 ${index + 1}`} className={FIELD} />
              </label>
            </div>
            <div className="mt-1.5 flex items-center justify-between gap-2">
              <span className="text-[11px] text-[var(--text-secondary)]">{q.basis}</span>
              <span className="flex gap-1">
                <button type="button" onClick={() => move(index, -1)} disabled={index === 0}
                  aria-label={`질문 ${index + 1} 위로`} className="rounded px-1.5 py-0.5 text-xs text-[var(--text-secondary)] disabled:opacity-40">↑</button>
                <button type="button" onClick={() => move(index, 1)} disabled={index === questions.length - 1}
                  aria-label={`질문 ${index + 1} 아래로`} className="rounded px-1.5 py-0.5 text-xs text-[var(--text-secondary)] disabled:opacity-40">↓</button>
                <button type="button" onClick={() => remove(index)}
                  aria-label={`질문 ${index + 1} 삭제`} className="rounded px-1.5 py-0.5 text-xs text-[var(--danger)]">삭제</button>
              </span>
            </div>
          </li>
        ))}
      </ol>

      <div className="flex gap-2">
        <label className="flex-1">
          <span className="sr-only">질문 추가</span>
          <input value={draftText} onChange={(e) => setDraftText(e.target.value)} placeholder="직접 물어볼 것을 적으세요"
            aria-label="질문 추가" className={FIELD}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
        </label>
        <button type="button" onClick={add} disabled={!draftText.trim()}
          className="shrink-0 rounded-md border border-[var(--border)] px-3 text-sm text-[var(--text-primary)] disabled:opacity-40">추가</button>
      </div>
    </section>
  );
}
