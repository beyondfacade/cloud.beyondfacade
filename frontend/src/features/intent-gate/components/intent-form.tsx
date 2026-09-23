"use client";

import { useRef, useState } from "react";
import styles from "./intent-gate.module.css";

/** 예시는 실제로 끝까지 이어지는 문장만 둔다. 셋째는 LLM 경로(랜드마크→동) 시연이다. */
export const EXAMPLE_CHIPS = ["역삼동에 카페, 예산 5천", "연남동에서 뭘 하면 좋을까", "홍대 근처 미용실"];

interface IntentFormProps {
  pending: boolean;
  onSubmit: (text: string) => void;
}

export function IntentForm({ pending, onSubmit }: IntentFormProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    onSubmit(trimmed);
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className={styles.form}>
        <label htmlFor="intent-text" className="text-[var(--landing-muted)]">어느 동네에서 무엇을 하려고 하세요?</label>
        <div className={styles.box}>
          <input
            id="intent-text"
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="예: 역삼동에 카페, 예산 5천"
            autoComplete="off"
          />
          <button type="submit" disabled={!text.trim() || pending}>
            {pending ? "찾는 중…" : "찾아보기"}<span aria-hidden="true">↗</span>
          </button>
        </div>
      </form>
      <div className={styles.chips} aria-label="예시 질문">
        {EXAMPLE_CHIPS.map((chip) => (
          <button key={chip} type="button" className={styles.chip} onClick={() => { setText(chip); inputRef.current?.focus(); }}>
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
