"use client";

import { INDUSTRIES, INDUSTRY_LABELS } from "@/shared/industries";
import { METRICS, METRIC_LABELS, YEARS, type MapState } from "../lib/map-state";

const FIELD =
  "rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-sm text-[var(--text-primary)] transition-colors hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

const LEGEND = "text-xs font-medium tracking-wide text-[var(--text-secondary)]";

interface ControlBarProps {
  state: MapState;
  onChange: (state: MapState) => void;
}

export function ControlBar({ state, onChange }: ControlBarProps) {
  return (
    <div className="flex flex-wrap items-end gap-x-6 gap-y-3 border-b border-[var(--border)] bg-[var(--bg-surface)] px-5 py-3">
      <label className="flex flex-col gap-1.5">
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

      <div className="flex flex-col gap-1.5">
        <span className={LEGEND} id="metric-legend">
          지표
        </span>
        <div
          role="group"
          aria-labelledby="metric-legend"
          className="flex gap-0.5 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-0.5"
        >
          {METRICS.map((m) => {
            const selected = state.metric === m;
            return (
              <button
                key={m}
                type="button"
                aria-pressed={selected}
                onClick={() => onChange({ ...state, metric: m })}
                className={`rounded px-3 py-1 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px ${
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

      <label className="flex flex-col gap-1.5">
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
