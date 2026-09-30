"use client";

import { useId, useState, type ReactNode } from "react";
import type { Tone } from "../lib/format";
import styles from "./admin.module.css";

export function Badge({ tone = "neutral", children, dot = false }: { tone?: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span className={styles.badge} data-tone={tone}>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      {children}
    </span>
  );
}

export interface StatItem {
  label: string;
  value: string;
  tone?: Tone;
  hint?: string;
  /** 숫자가 아닌 긴 텍스트 값(호스트명 등) — 한 줄 말줄임. */
  compact?: boolean;
}

export function StatStrip({ items, label }: { items: StatItem[]; label: string }) {
  return (
    <dl className={styles.stats} aria-label={label}>
      {items.map((item) => (
        <div key={item.label} className={styles.stat}>
          <dt className={styles.statLabel}>{item.label}</dt>
          <dd
            className={styles.statValue}
            data-tone={item.tone}
            data-size={item.compact ? "compact" : undefined}
            title={item.compact ? item.value : undefined}
          >
            {item.value}
          </dd>
          {item.hint && <dd className={styles.statHint}>{item.hint}</dd>}
        </div>
      ))}
    </dl>
  );
}

export interface TabDef {
  key: string;
  label: string;
  count?: number;
  render: () => ReactNode;
}

/** 탭 레지스트리 — 방마다 [{key,label,render}]만 넘긴다. 키보드 좌우 이동은 WAI-ARIA tabs 패턴. */
export function Tabs({ tabs, label }: { tabs: TabDef[]; label: string }) {
  const [active, setActive] = useState(tabs[0].key);
  const id = useId();
  const current = tabs.find((t) => t.key === active) ?? tabs[0];

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = tabs[(index + step + tabs.length) % tabs.length];
    setActive(next.key);
    document.getElementById(`${id}-tab-${next.key}`)?.focus();
  }

  return (
    <>
      <div className={styles.tabs} role="tablist" aria-label={label}>
        {tabs.map((tab, index) => (
          <button
            key={tab.key}
            id={`${id}-tab-${tab.key}`}
            type="button"
            role="tab"
            className={styles.tab}
            aria-selected={tab.key === current.key}
            aria-controls={`${id}-panel`}
            tabIndex={tab.key === current.key ? 0 : -1}
            onClick={() => setActive(tab.key)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {tab.label}
            {tab.count !== undefined && <span className={styles.tabCount}>{tab.count}</span>}
          </button>
        ))}
      </div>
      <div
        key={current.key}
        id={`${id}-panel`}
        role="tabpanel"
        aria-labelledby={`${id}-tab-${current.key}`}
        className={styles.tabPanel}
      >
        {current.render()}
      </div>
    </>
  );
}

export function Section({ title, aside, children, flush = false }: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  flush?: boolean;
}) {
  return (
    <section className={styles.section} aria-label={title}>
      <header className={styles.sectionHead}>
        <h2>{title}</h2>
        {aside}
      </header>
      {flush ? children : <div className={styles.sectionBody}>{children}</div>}
    </section>
  );
}

export function Meter({ label, percent, tone, detail }: { label: string; percent: number | null; tone: Tone; detail: string }) {
  const width = Math.min(100, Math.max(0, percent ?? 0));
  return (
    <div className={styles.meter}>
      <div className={styles.meterHead}>
        <span>{label}</span>
        <strong>{percent == null ? "—" : `${percent}%`}</strong>
      </div>
      <div
        className={styles.meterTrack}
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent ?? undefined}
      >
        <div className={styles.meterFill} data-tone={tone} style={{ width: `${width}%` }} />
      </div>
      <span className={styles.meterFoot}>{detail}</span>
    </div>
  );
}

/** 세션 동안 모은 값의 스파크라인 — 서버 이력이 아니라 이 화면을 연 뒤의 폴링 값이다. */
export function Sparkline({ values, max, label }: { values: number[]; max: number; label: string }) {
  if (values.length < 2) return null;
  const w = 200;
  const h = 44;
  const step = w / (values.length - 1);
  const points = values.map((v, i) => `${(i * step).toFixed(1)},${(h - 2 - (Math.min(v, max) / max) * (h - 4)).toFixed(1)}`);
  return (
    <svg className={styles.spark} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label={label}>
      <polyline points={`0,${h} ${points.join(" ")} ${w},${h}`} fill="currentColor" opacity=".12" stroke="none" />
      <polyline points={points.join(" ")} fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <p className={styles.notice} role="note">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6.5" stroke="currentColor" /><path d="M8 7v4M8 5v.01" stroke="currentColor" strokeLinecap="round" /></svg>
      <span>{children}</span>
    </p>
  );
}

export function RoomError({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "알 수 없는 오류";
  return <Notice>스냅샷을 불러오지 못했습니다 — {message}</Notice>;
}
