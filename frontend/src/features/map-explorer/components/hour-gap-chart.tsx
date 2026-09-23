"use client";

import { useQuery } from "@tanstack/react-query";
import type { HourGapBand, RegionIndustryHourGap } from "@/shared/api/types";
import { ApiError } from "@/shared/api/client";
import { industryLabel } from "@/shared/industries";
import { withTopicParticle } from "@/shared/korean";
import { HOUR_BANDS, hourBandLabel } from "@/shared/neighborhood";
import { fetchHourGaps } from "../api";
import { hourGapSentence } from "../lib/hour-gap-sentence";

const W = 280;
const H = 120;
const PAD_BOTTOM = 18;
const PAD_TOP = 6;
const PLOT_H = H - PAD_BOTTOM - PAD_TOP;

/** 6구간 라벨의 짧은 형태("점심") — x축은 자리가 좁다. 긴 형태는 문장이 쓴다. */
function shortLabel(band: string): string {
  return hourBandLabel(band).replace(/\(.*\)$/, "");
}

/** 두 선 — 유동 강도와 매출 강도를 같은 6구간 위에 겹친다. gap 막대는 그리지 않는다.
 *  어긋남의 신호는 절대 부호가 아니라 상대 위치에 있다(v0.26.0 검증) — 두 선이 벌어지는 자리가 그것이다. */
export function HourGapLines({ bands }: { bands: HourGapBand[] }) {
  const ordered = HOUR_BANDS.map((b) => bands.find((x) => x.hour_band === b)).filter((x): x is HourGapBand => !!x);
  const max = Math.max(1, ...ordered.flatMap((b) => [b.footfall_intensity, b.sales_intensity]));
  const step = W / Math.max(1, ordered.length);
  const x = (i: number) => step * i + step / 2;
  const y = (v: number) => PAD_TOP + PLOT_H - (v / max) * PLOT_H;
  const points = (pick: (b: HourGapBand) => number) => ordered.map((b, i) => `${x(i)},${y(pick(b))}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="시간대별 유동 강도와 매출 강도">
      <line x1={0} x2={W} y1={y(1)} y2={y(1)} stroke="var(--border)" strokeDasharray="3 3" />
      <polyline data-series="footfall" points={points((b) => b.footfall_intensity)} fill="none" stroke="var(--text-secondary)" strokeWidth={1.5} />
      <polyline data-series="sales" points={points((b) => b.sales_intensity)} fill="none" stroke="var(--accent)" strokeWidth={2} />
      {ordered.map((b, i) => (
        <text key={b.hour_band} x={x(i)} y={H - 4} textAnchor="middle" fontSize={10} fill="var(--text-secondary)">
          {shortLabel(b.hour_band)}
        </text>
      ))}
    </svg>
  );
}

export function HourGapBody({ gap }: { gap: RegionIndustryHourGap }) {
  const sentence = hourGapSentence(gap.bands);
  return (
    <>
      <HourGapLines bands={gap.bands} />
      <p className="flex gap-3 text-xs text-[var(--text-secondary)]">
        <span><span aria-hidden className="mr-1 inline-block h-0.5 w-3 align-middle bg-[var(--text-secondary)]" />유동인구</span>
        <span><span aria-hidden className="mr-1 inline-block h-0.5 w-3 align-middle bg-[var(--accent)]" />매출</span>
        <span>점선 = 하루 평균</span>
      </p>
      {sentence && <p className="text-sm leading-relaxed text-[var(--text-primary)]">{sentence}</p>}
      <p className="text-xs tabular-nums text-[var(--text-secondary)]">기준 {gap.year_quarter.slice(0, 4)}년 {gap.year_quarter.slice(4)}분기</p>
    </>
  );
}

/** 패널 ③ 내 업종은 언제 돈이 도나 — 업종에 따라 바뀐다. 매출 자료가 없는 조합(404)은 한 줄로 말한다. */
export function HourGapSection({ regionCode, industry }: { regionCode: string; industry: string }) {
  const gap = useQuery({
    queryKey: ["hour-gaps", regionCode, industry],
    queryFn: () => fetchHourGaps(regionCode, industry),
    retry: false,
  });
  const notFound = gap.isError && gap.error instanceof ApiError && gap.error.code === "HOUR_GAP_NOT_FOUND";
  return (
    <section className="mt-7 flex flex-col gap-3" aria-label="업종 시간대">
      <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">
        {withTopicParticle(industryLabel(industry))} 언제 돈이 도나
      </h3>
      {gap.isPending && <div className="h-28 rounded bg-[var(--bg-raised)]" role="status" aria-label="불러오는 중" />}
      {notFound && (
        <p className="text-sm text-[var(--text-secondary)]">이 동네엔 {industryLabel(industry)} 매출 자료가 없습니다.</p>
      )}
      {gap.isError && !notFound && (
        <p role="alert" className="text-sm text-[var(--danger)]">시간대 자료를 불러오지 못했습니다.</p>
      )}
      {gap.data && <HourGapBody gap={gap.data} />}
    </section>
  );
}
