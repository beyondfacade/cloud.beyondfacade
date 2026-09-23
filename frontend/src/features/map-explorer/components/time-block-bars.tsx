"use client";

import type { BlockIntensities, RegionProfile } from "@/shared/api/types";
import { TIME_BLOCKS, TIME_BLOCK_LABELS, phasesNarrative, timeLabelSentence } from "@/shared/neighborhood";
import { useRegionProfile } from "../hooks/use-region-profile";

const W = 280;
const H = 96;
const PAD_BOTTOM = 18; // 블록 이름 자리
const PLOT_H = H - PAD_BOTTOM;
const GAP = 10;
const BAR_W = (W - GAP * (TIME_BLOCKS.length + 1)) / TIME_BLOCKS.length;

/** 4블록 막대 — 배치가 준 시간당 강도를 그대로 그린다. 1.0(하루 평균) 기준선, 정점 블록만 강조색.
 *  DOM SVG는 CSS `var()`를 읽으므로 MapLibre와 달리 계산된 색을 넘길 필요가 없다. */
export function TimeBlockBars({ blocks, peak }: { blocks: BlockIntensities; peak: string | null }) {
  const max = Math.max(1, ...TIME_BLOCKS.map((b) => blocks[b]));
  const y = (v: number) => PLOT_H - (v / max) * PLOT_H;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="하루 4블록 유동 강도">
      <line x1={0} x2={W} y1={y(1)} y2={y(1)} stroke="var(--border)" strokeDasharray="3 3" />
      {TIME_BLOCKS.map((block, i) => {
        const x = GAP + i * (BAR_W + GAP);
        const top = y(blocks[block]);
        return (
          <g key={block}>
            <rect
              x={x}
              y={top}
              width={BAR_W}
              height={PLOT_H - top}
              rx={3}
              fill={block === peak ? "var(--accent)" : "var(--bg-raised)"}
              stroke={block === peak ? "none" : "var(--border)"}
              data-block={block}
              data-peak={block === peak ? "true" : undefined}
            />
            <text x={x + BAR_W / 2} y={H - 4} textAnchor="middle" fontSize={11} fill="var(--text-secondary)">
              {TIME_BLOCK_LABELS[block]}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function TimeBlockBody({ profile }: { profile: RegionProfile }) {
  // 정점→바닥 서사가 없는 조합이면 시간대 라벨 문장으로 물러선다 (분류 문서 §6-4)
  const narrative =
    phasesNarrative(profile.peak_block, profile.trough_block) ?? timeLabelSentence(profile.time_label);
  return (
    <>
      {profile.block_intensities ? (
        <TimeBlockBars blocks={profile.block_intensities} peak={profile.peak_block} />
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">시간대 자료가 없습니다.</p>
      )}
      {narrative && <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{narrative}</p>}
      <p className="text-xs text-[var(--text-secondary)]">점선이 하루 평균(1.00) · 강조가 정점 블록</p>
    </>
  );
}

/** 패널 ② 하루가 어떻게 흐르나 — 프로필 조회는 ①과 같은 키라 요청이 한 번이다. */
export function TimeBlockSection({ regionCode }: { regionCode: string }) {
  const profile = useRegionProfile(regionCode);
  return (
    <section className="mt-7 flex flex-col gap-3" aria-label="하루 흐름">
      <h3 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">하루가 어떻게 흐르나</h3>
      {profile.isPending && <div className="h-24 rounded bg-[var(--bg-raised)]" role="status" aria-label="불러오는 중" />}
      {profile.isError && <p role="alert" className="text-sm text-[var(--danger)]">하루 흐름을 불러오지 못했습니다.</p>}
      {profile.data && <TimeBlockBody profile={profile.data} />}
    </section>
  );
}
