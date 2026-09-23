"use client";

import { INDUSTRIES, INDUSTRY_LABELS } from "@/shared/industries";
import { METRICS, METRIC_LABELS, YEARS, type MapState } from "../lib/map-state";
import styles from "./map-workspace.module.css";

const FIELD =
  "min-h-10 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

const LEGEND = "text-xs font-medium tracking-wide text-[var(--text-secondary)]";

interface ControlBarProps {
  state: MapState;
  onChange: (state: MapState) => void;
}

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
          {INDUSTRIES.map((ind) => (
            <option key={ind} value={ind}>
              {INDUSTRY_LABELS[ind]}
            </option>
          ))}
        </select>
      </label>

      <div className={`${styles.metricField} flex flex-col gap-2`}>
        <span className={LEGEND} id="metric-legend">
          지표
        </span>
        <div
          role="group"
          aria-labelledby="metric-legend"
          className="flex gap-1 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-1"
        >
          {METRICS.map((m) => {
            const selected = state.metric === m;
            return (
              <button
                key={m}
                type="button"
                aria-pressed={selected}
                onClick={() => onChange({ ...state, metric: m })}
                className={`min-h-8 flex-1 whitespace-nowrap rounded-md px-4 py-1 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px ${
                  selected
                    ? "bg-[var(--accent)] text-[var(--accent-fg)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
                }`}
              >
                {METRIC_LABELS[m]}
              </button>
            );
          })}
        </div>
      </div>

      <label className={`${styles.yearField} flex flex-col gap-2`}>
        <span className={LEGEND}>연도</span>
        <select
          value={state.year}
          onChange={(e) => onChange({ ...state, year: Number(e.target.value) })}
          className={`${FIELD} tabular-nums`}
        >
          {YEARS.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
