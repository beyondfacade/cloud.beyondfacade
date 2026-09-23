"use client";

import styles from "./intent-gate.module.css";

export interface ChipOption {
  key: string;
  label: string;
}

interface ClarifyChipsProps {
  prompt: string;
  options: ChipOption[];
  onPick: (key: string) => void;
  /** 답을 모를 때의 우회로 — 점선 칩으로 구분한다. */
  escape?: { label: string; onPick: () => void };
}

/** 되묻기 칩. 칩 선택은 재제출이 아니다 — 부모가 응답 객체를 채워 다음 단계로 간다. */
export function ClarifyChips({ prompt, options, onPick, escape }: ClarifyChipsProps) {
  return (
    <div className={styles.prompt} aria-live="polite">
      <p>{prompt}</p>
      <div className={styles.chips}>
        {options.map((option) => (
          <button key={option.key} type="button" className={styles.chip} onClick={() => onPick(option.key)}>
            {option.label}
          </button>
        ))}
        {escape && (
          <button type="button" className={`${styles.chip} ${styles.chipEscape}`} onClick={escape.onPick}>
            {escape.label}
          </button>
        )}
      </div>
    </div>
  );
}
