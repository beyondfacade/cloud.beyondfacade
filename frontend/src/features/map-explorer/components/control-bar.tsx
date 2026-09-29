"use client";

import { INDUSTRY_GROUPS, INDUSTRY_LABELS } from "@/shared/industries";
import type { MapState } from "../lib/map-state";
import styles from "./map-workspace.module.css";

const FIELD =
  "min-h-10 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

const LEGEND = "text-xs font-medium tracking-wide text-[var(--text-secondary)]";

interface ControlBarProps {
  state: MapState;
  onChange: (state: MapState) => void;
}

/** 최신 판정 지도의 업종 선택기. */
export function ControlBar({ state, onChange }: ControlBarProps) {
  return (
    <div className={styles.filterTray}>
      <div className={styles.filterIntro}><span className={styles.eyebrow}>YOUR PERSPECTIVE</span><span>어떤 상권이 궁금하세요?</span></div>
      <label className={`${styles.industryField} flex flex-col gap-2`}>
        <span className={LEGEND}>업종</span>
        <select
          value={state.industry}
          onChange={(e) => onChange({ ...state, industry: e.target.value })}
          className={FIELD}
        >
          {INDUSTRY_GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.ids.map((ind) => (
                <option key={ind} value={ind}>
                  {INDUSTRY_LABELS[ind]}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
    </div>
  );
}
