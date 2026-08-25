"use client";

import { useState } from "react";
import type { StartAnalysisParams } from "../hooks/use-agent-report";

interface AnalysisFormProps {
  initialRegion: string;
  initialIndustry: string;
  onSubmit: (params: StartAnalysisParams) => void;
  disabled?: boolean;
}

export function AnalysisForm({ initialRegion, initialIndustry, onSubmit, disabled }: AnalysisFormProps) {
  const [region, setRegion] = useState(initialRegion);
  const [industry, setIndustry] = useState(initialIndustry);
  const [question, setQuestion] = useState("");

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ region, industry, question: question.trim() || undefined });
      }}
    >
      <label className="flex flex-col gap-1 text-sm text-[var(--text-secondary)]">
        지역 코드
        <input
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          className="rounded border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm text-[var(--text-secondary)]">
        업종
        <input
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          className="rounded border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm text-[var(--text-secondary)]">
        추가 질문 (선택)
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          className="rounded border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]"
        />
      </label>
      <button
        type="submit"
        disabled={disabled || !region || !industry}
        className="rounded bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[var(--accent-fg)] disabled:opacity-50"
      >
        분석 시작
      </button>
    </form>
  );
}
