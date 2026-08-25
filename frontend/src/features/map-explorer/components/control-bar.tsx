"use client";

import {
  INDUSTRIES,
  METRICS,
  YEARS,
  type MapState,
} from "../lib/map-state";

interface ControlBarProps {
  state: MapState;
  onChange: (state: MapState) => void;
}

export function ControlBar({ state, onChange }: ControlBarProps) {
  return (
    <div className="flex items-center gap-4 border-b border-[var(--border-color)] bg-[var(--bg-surface)] px-4 py-3">
      {/* Industry Select */}
      <select
        value={state.industry}
        onChange={(e) => onChange({ ...state, industry: e.target.value })}
        className="rounded border border-[var(--border-color)] bg-[var(--bg-surface)] px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      >
        {INDUSTRIES.map((ind) => (
          <option key={ind} value={ind}>
            {ind}
          </option>
        ))}
      </select>

      {/* Metric Segment */}
      <div className="flex gap-1 rounded border border-[var(--border-color)] bg-[var(--bg-surface)] p-0.5">
        {METRICS.map((m) => (
          <button
            key={m}
            onClick={() => onChange({ ...state, metric: m })}
            className={`px-3 py-1 text-sm font-medium transition-colors ${
              state.metric === m
                ? "bg-[var(--accent)] text-[var(--accent-fg)]"
                : "bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Year Select */}
      <select
        value={state.year}
        onChange={(e) => onChange({ ...state, year: Number(e.target.value) })}
        className="rounded border border-[var(--border-color)] bg-[var(--bg-surface)] px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      >
        {YEARS.map((year) => (
          <option key={year} value={year}>
            {year}
          </option>
        ))}
      </select>
    </div>
  );
}
