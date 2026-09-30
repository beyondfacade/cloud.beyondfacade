"use client";

import { useState, type PointerEvent } from "react";
import { Empty } from "./admin-ui";
import styles from "./admin.module.css";

export type ChartTone = "accent" | "ok" | "warn" | "danger" | "muted";

export interface ChartSeries {
  key: string;
  label: string;
  tone: ChartTone;
  values: (number | null)[];
  /** 톤이 모자랄 때 같은 색을 점선으로 구분한다(꺾은선 전용). */
  dashed?: boolean;
}

const W = 600;
const H = 160;
const PAD = 6;

/** 포인터 x → 가장 가까운 칸 인덱스. 벗어나면 null(최신 값 표시로 돌아간다). */
function useHoverIndex(count: number) {
  const [index, setIndex] = useState<number | null>(null);
  function onPointerMove(event: PointerEvent<SVGSVGElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    if (!box.width || count < 1) return;
    const ratio = (event.clientX - box.left) / box.width;
    setIndex(Math.min(count - 1, Math.max(0, Math.round(ratio * (count - 1)))));
  }
  return { index, bind: { onPointerMove, onPointerLeave: () => setIndex(null) } };
}

function Legend({ series, index, format }: { series: ChartSeries[]; index: number; format: (v: number | null) => string }) {
  return (
    <ul className={styles.legend}>
      {series.map((s) => (
        <li key={s.key}>
          <span className={styles.legendSwatch} data-tone={s.tone} data-dashed={s.dashed || undefined} aria-hidden="true" />
          {s.label}
          <strong>{format(s.values[index] ?? null)}</strong>
        </li>
      ))}
    </ul>
  );
}

function Axis({ labels }: { labels: string[] }) {
  const ticks = labels.length > 2 ? [labels[0], labels[Math.floor(labels.length / 2)], labels[labels.length - 1]] : labels;
  return (
    <div className={styles.axis} aria-hidden="true">
      {ticks.map((t, i) => <span key={`${t}-${i}`}>{t}</span>)}
    </div>
  );
}

/** null 구간은 끊어 그린다 — 표본이 빈 시간을 선으로 잇지 않는다. */
function segments(values: (number | null)[], x: (i: number) => number, y: (v: number) => number): string[] {
  const out: string[] = [];
  let run: string[] = [];
  values.forEach((v, i) => {
    if (v == null) {
      if (run.length) out.push(run.join(" "));
      run = [];
    } else {
      run.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    }
  });
  if (run.length) out.push(run.join(" "));
  return out;
}

/** 서버 이력 꺾은선 — max를 주면 고정 축(백분율 등), 아니면 자료 최댓값. */
export function TrendChart({ label, labels, series, max, format }: {
  label: string;
  labels: string[];
  series: ChartSeries[];
  max?: number;
  format: (v: number | null) => string;
}) {
  const { index, bind } = useHoverIndex(labels.length);
  if (labels.length < 2) return <Empty>아직 표본이 부족합니다.</Empty>;
  const top = max ?? Math.max(1, ...series.flatMap((s) => s.values.filter((v): v is number => v != null)));
  const x = (i: number) => (i / (labels.length - 1)) * W;
  const y = (v: number) => H - PAD - (Math.min(v, top) / top) * (H - PAD * 2);
  const at = index ?? labels.length - 1;
  return (
    <figure className={styles.chart}>
      <figcaption className={styles.chartHead}>
        <span>{label}</span>
        <span className={styles.muted}>{index == null ? "최신" : labels[at]}</span>
      </figcaption>
      <svg className={styles.chartSvg} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={label} {...bind}>
        {[0.25, 0.5, 0.75].map((f) => <line key={f} className={styles.chartGrid} x1={0} x2={W} y1={H * f} y2={H * f} />)}
        {series.map((s) => segments(s.values, x, y).map((points, i) => (
          <polyline key={`${s.key}-${i}`} className={styles.chartLine} data-tone={s.tone} data-dashed={s.dashed || undefined} points={points} />
        )))}
        {index != null && <line className={styles.chartCursor} x1={x(at)} x2={x(at)} y1={0} y2={H} />}
      </svg>
      <Axis labels={labels} />
      <Legend series={series} index={at} format={format} />
    </figure>
  );
}

/** 칸별 누적 막대 — series 순서대로 아래부터 쌓는다. */
export function StackedBars({ label, labels, series, format }: {
  label: string;
  labels: string[];
  series: ChartSeries[];
  format: (v: number | null) => string;
}) {
  const { index, bind } = useHoverIndex(labels.length);
  if (!labels.length) return <Empty>표시할 구간이 없습니다.</Empty>;
  const totals = labels.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] ?? 0), 0));
  const top = Math.max(1, ...totals);
  const slot = W / labels.length;
  const bar = Math.max(1, slot * 0.72);
  const at = index ?? labels.length - 1;
  return (
    <figure className={styles.chart}>
      <figcaption className={styles.chartHead}>
        <span>{label}</span>
        <span className={styles.muted}>{labels[at]} · 합계 {format(totals[at])}</span>
      </figcaption>
      <svg className={styles.chartSvg} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={label} {...bind}>
        {[0.25, 0.5, 0.75].map((f) => <line key={f} className={styles.chartGrid} x1={0} x2={W} y1={H * f} y2={H * f} />)}
        {labels.map((l, i) => {
          let base = H;
          return (
            <g key={`${l}-${i}`} opacity={index == null || index === i ? 1 : 0.45}>
              {series.map((s) => {
                const h = ((s.values[i] ?? 0) / top) * (H - PAD);
                base -= h;
                return h > 0 ? <rect key={s.key} className={styles.chartBar} data-tone={s.tone} x={i * slot + (slot - bar) / 2} y={base} width={bar} height={h} /> : null;
              })}
            </g>
          );
        })}
      </svg>
      <Axis labels={labels} />
      <Legend series={series} index={at} format={format} />
    </figure>
  );
}
