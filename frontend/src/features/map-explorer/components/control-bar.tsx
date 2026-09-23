"use client";

import { INDUSTRIES, INDUSTRY_LABELS } from "@/shared/industries";
import { METRIC_GROUPS, METRIC_LABELS, YEARS, metricGroupOf, type MapState } from "../lib/map-state";
import { LATEST_QUARTER, QUARTERS, formatQuarter } from "../lib/quarters";
import styles from "./map-workspace.module.css";

const FIELD =
  "min-h-10 rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors hover:border-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

const LEGEND = "text-xs font-medium tracking-wide text-[var(--text-secondary)]";

const INDUSTRY_NOTE_ID = "industry-axis-note";

interface ControlBarProps {
  state: MapState;
  onChange: (state: MapState) => void;
}

/** 지표 버튼 두 무리 + 축을 따라가는 셀렉터.
 *  무리 자체가 모드다 — 동네 무리를 고르면 업종 select가 흐려지고(값은 살아 있다: 사이드패널·마커가 쓴다)
 *  시간 셀렉터가 연도에서 분기로 바뀐다. 연 데이터를 분기로 위장하지 않고, 분기 데이터에 연도를 묻지 않는다. */
export function ControlBar({ state, onChange }: ControlBarProps) {
  const group = metricGroupOf(state.metric);
  const regionAxis = group.axis === "region_quarter";

  return (
    <div className={styles.filterTray}>
      <div className={styles.filterIntro}><span className={styles.eyebrow}>YOUR PERSPECTIVE</span><span>어떤 상권이 궁금하세요?</span></div>
      <label className={`${styles.industryField} flex flex-col gap-2 ${regionAxis ? styles.axisMuted : ""}`}>
        <span className={LEGEND}>업종</span>
        <select
          value={state.industry}
          onChange={(e) => onChange({ ...state, industry: e.target.value })}
          className={FIELD}
          aria-describedby={regionAxis ? INDUSTRY_NOTE_ID : undefined}
        >
          {INDUSTRIES.map((ind) => (
            <option key={ind} value={ind}>
              {INDUSTRY_LABELS[ind]}
            </option>
          ))}
        </select>
        {regionAxis && (
          <span id={INDUSTRY_NOTE_ID} className="text-[11px] leading-none text-[var(--text-secondary)]">
            이 지표는 업종과 무관합니다
          </span>
        )}
      </label>

      <div className={`${styles.metricField} flex flex-col gap-2`}>
        <span className={LEGEND} id="metric-legend">
          지표
        </span>
        <div className={styles.metricGroups} aria-labelledby="metric-legend">
          {METRIC_GROUPS.map((g) => (
            <div key={g.key} role="group" aria-label={g.label} className={styles.metricGroup}>
              <span className={styles.metricGroupLabel}>{g.label}</span>
              <div className="flex gap-1 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-1">
                {g.metrics.map((m) => {
                  const selected = state.metric === m;
                  return (
                    <button
                      key={m}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => onChange({ ...state, metric: m })}
                      className={`min-h-8 flex-1 whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px ${
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
          ))}
        </div>
      </div>

      {regionAxis ? (
        <label className={`${styles.yearField} flex flex-col gap-2`}>
          <span className={LEGEND}>분기</span>
          <select
            // null(최신)은 목록의 마지막 분기로 보인다. 최신을 고르면 다시 null로 둬 URL을 짧게 유지한다
            value={state.year_quarter ?? LATEST_QUARTER}
            onChange={(e) => onChange({ ...state, year_quarter: e.target.value === LATEST_QUARTER ? null : e.target.value })}
            className={`${FIELD} tabular-nums`}
          >
            {QUARTERS.map((yq) => (
              <option key={yq} value={yq}>
                {formatQuarter(yq)}
              </option>
            ))}
          </select>
        </label>
      ) : (
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
      )}
    </div>
  );
}
