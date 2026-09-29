"use client";

import type { RegionProfile, UnavailableFact } from "@/shared/api/types";
import { timeLabelSentence } from "@/shared/neighborhood";
import { TIME_BLOCKS, TIME_BLOCK_LABELS, phasesNarrative } from "../../lib/neighborhood-charts";
import { availableFact } from "../../lib/available-fact";

/** 원천의 시간당 강도를 CSS 막대로 표시한다. 1.00은 하루 평균, 강조는 정점이다. */
export function TimeBlockBody({ profile }: { profile: RegionProfile }) {
  const blocks = profile.block_intensities;
  if (!blocks || TIME_BLOCKS.some((b) => !Number.isFinite(blocks[b]))) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  const max = Math.max(1, ...TIME_BLOCKS.map((b) => blocks[b]));
  const narrative = phasesNarrative(profile.peak_block, profile.trough_block) ?? timeLabelSentence(profile.time_label);
  return <>
    <div role="img" aria-label="하루 4블록 유동 강도" className="relative pt-2">
      <div className="relative flex h-28 items-end justify-around gap-3">
        <div className="absolute inset-x-0 border-t border-dashed border-[var(--border)]" style={{ bottom: `${100 / max}%` }} />
        {TIME_BLOCKS.map((block) => <div key={block} data-block={block} data-peak={block === profile.peak_block ? "true" : undefined}
          title={`${TIME_BLOCK_LABELS[block]}: ${blocks[block].toFixed(2)}`}
          className="relative w-1/5 rounded-t border border-[var(--border)]"
          style={{ height: `${Math.max(0, blocks[block]) / max * 100}%`, backgroundColor: block === profile.peak_block ? "var(--accent)" : "var(--bg-raised)" }} />)}
      </div>
      <div className="mt-1 flex justify-around gap-3 text-xs text-[var(--text-secondary)]">
        {TIME_BLOCKS.map((block) => <span key={block} className="w-1/5 text-center">{TIME_BLOCK_LABELS[block]}</span>)}
      </div>
    </div>
    {narrative && <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{narrative}</p>}
    <p className="text-xs text-[var(--text-secondary)]">점선이 하루 평균(1.00) · 강조가 정점 블록</p>
    {profile.year_quarter && <p className="text-xs text-[var(--text-secondary)]">기준 {profile.year_quarter.slice(0, 4)}년 {profile.year_quarter.slice(4)}분기</p>}
  </>;
}

export function TimeBlockBars({ profile }: { profile?: RegionProfile | UnavailableFact }) {
  const data = availableFact(profile);
  if (!data) return <p className="text-sm text-[var(--text-secondary)]">자료 없음</p>;
  return <section className="flex flex-col gap-3" aria-label="하루 흐름">
    <h3 className="text-sm font-semibold text-[var(--text-primary)]">하루가 어떻게 흐르나</h3>
    <TimeBlockBody profile={data} />
  </section>;
}
