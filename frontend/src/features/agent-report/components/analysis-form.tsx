"use client";

import { useState } from "react";
import { industryLabel } from "@/shared/industries";
import type { StartAnalysisParams } from "../hooks/use-agent-report";

interface AnalysisFormProps {
  initialRegion: string;
  initialIndustry: string;
  onSubmit: (params: StartAnalysisParams) => void;
  disabled?: boolean;
}

const FIELD =
  "rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

export function AnalysisForm({ initialRegion, initialIndustry, onSubmit, disabled }: AnalysisFormProps) {
  const [region, setRegion] = useState(initialRegion);
  const [industry, setIndustry] = useState(initialIndustry);
  const [question, setQuestion] = useState("");

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ region, industry, question: question.trim() || undefined });
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
          지역 코드
          <input
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className={`${FIELD} tabular-nums`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
          업종
          <input value={industry} onChange={(e) => setIndustry(e.target.value)} className={FIELD} />
          {/* 입력값은 API 계약상의 업종 id다. 무엇을 가리키는 id인지 한국어 라벨로 함께 보여준다. */}
          <span className="font-normal text-[var(--text-secondary)]">
            {industry ? industryLabel(industry) : "지도 탐색 탭에서 업종을 고르면 자동으로 채워집니다"}
          </span>
        </label>
      </div>
      <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
        추가 질문 (선택)
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          placeholder="예: 원두 가격이 오르면 손익분기점이 어떻게 달라지나요?"
          className={`${FIELD} resize-y placeholder:text-[var(--text-secondary)]`}
        />
      </label>
      <button
        type="submit"
        disabled={disabled || !region || !industry}
        className="self-start rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
      >
        {disabled ? "분석 중…" : "분석 시작"}
      </button>
    </form>
  );
}
