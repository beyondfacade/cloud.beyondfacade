"use client";

import { useState } from "react";
import { INDUSTRIES, industryLabel, type IndustryId } from "@/shared/industries";
import type { StartAnalysisParams } from "../hooks/use-agent-report";
import styles from "./analysis-workspace.module.css";

interface AnalysisFormProps {
  initialRegion: string;
  initialIndustry: string;
  onSubmit: (params: StartAnalysisParams) => void;
  disabled?: boolean;
}

const FIELD =
  `${styles.field} border border-[var(--border)] bg-[var(--bg-base)] text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]`;

export function AnalysisForm({ initialRegion, initialIndustry, onSubmit, disabled }: AnalysisFormProps) {
  const [region, setRegion] = useState(initialRegion);
  const [industry, setIndustry] = useState(initialIndustry);
  const [question, setQuestion] = useState("");

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ region, industry, question: question.trim() || undefined });
      }}
    >
      <div className={styles.formFields}>
        <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
          지역 코드
          <input
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="예: 1168064000"
            className={`${FIELD} tabular-nums`}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
          업종
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className={FIELD}
          >
            {!INDUSTRIES.includes(industry as IndustryId) && industry ? (
              <option value={industry}>{industryLabel(industry)}</option>
            ) : null}
            {INDUSTRIES.map((id) => (
              <option key={id} value={id}>
                {industryLabel(id)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
        추가 질문 (선택)
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={4}
          placeholder="예: 원두 가격이 오르면 손익분기점이 어떻게 달라지나요?"
          className={`${FIELD} resize-y placeholder:text-[var(--text-secondary)]`}
        />
      </label>
      <button
        type="submit"
        disabled={disabled || !region || !industry}
        className={`${styles.submitButton} bg-[var(--accent)] text-[var(--accent-fg)] hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50`}
      >
        {disabled ? "분석 중…" : "분석 시작"}
        <span aria-hidden="true">→</span>
      </button>
    </form>
  );
}
