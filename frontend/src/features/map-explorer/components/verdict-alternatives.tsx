"use client";

import type { VerdictCode } from "@/shared/api/types";
import { industryLabel } from "@/shared/industries";
import { withConditionalParticle } from "@/shared/korean";
import { neighborhoodTypeLabel } from "@/shared/neighborhood";
import { verdictLabel } from "@/shared/verdict";
import { useVerdictAlternatives } from "../hooks/use-verdict-alternatives";

/** 대안 항목의 판정 라벨 색 — 경고 없음은 보조 텍스트, 조건부는 --warn (대안은 이 둘뿐, 설계서 §12). */
const ALT_TOKEN: Partial<Record<VerdictCode, string>> = { clear: "var(--text-secondary)", orange: "var(--warn)" };

interface Item {
  id: string;
  name: string;
  verdict_code: VerdictCode;
}

function Line({ testId, lead, items, note }: { testId: string; lead: string; items: Item[]; note?: string }) {
  return (
    <div data-testid={testId} className="text-sm leading-snug">
      <span className="text-[var(--text-secondary)]">{lead} </span>
      {items.map((item, i) => (
        <span key={item.id}>
          {i > 0 && <span className="text-[var(--text-secondary)]"> · </span>}
          <span className="font-medium text-[var(--text-primary)]">{item.name}</span>
          <span className="ml-0.5 text-[11px]" style={{ color: ALT_TOKEN[item.verdict_code] }}>
            {verdictLabel(item.verdict_code).name}
          </span>
        </span>
      ))}
      {note && <span className="ml-1 text-[11px] text-[var(--text-secondary)]">({note})</span>}
    </div>
  );
}

interface VerdictAlternativesProps {
  regionCode: string;
  industry: string;
}

/** 판정 카드의 "대안 2줄" — 동네 고정(다른 업종) · 업종 고정(같은 유형의 다른 동). 로딩·오류·빈 결과는 아무것도 그리지 않는다:
 *  카드 본체가 이미 판정을 보여주고 있어 여기서 또 안내문을 띄우면 소음이다. */
export function VerdictAlternatives({ regionCode, industry }: VerdictAlternativesProps) {
  const query = useVerdictAlternatives(regionCode, industry);
  if (!query.isSuccess) return null;
  const { industries, regions, neighborhood_type } = query.data;
  if (industries.length === 0 && regions.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 border-t border-[var(--border)] pt-2" aria-label="대안">
      {industries.length > 0 && (
        <Line
          testId="alt-industries"
          lead="굳이 이 동네라면"
          items={industries.map((a) => ({ id: a.industry_id, name: a.industry_name, verdict_code: a.verdict_code }))}
        />
      )}
      {regions.length > 0 && (
        <Line
          testId="alt-regions"
          lead={`굳이 ${withConditionalParticle(industryLabel(industry))}`}
          items={regions.map((a) => ({ id: a.region_code, name: a.region_name, verdict_code: a.verdict_code }))}
          note={neighborhood_type ? `같은 ${neighborhoodTypeLabel(neighborhood_type).name} 동네 중` : undefined}
        />
      )}
    </div>
  );
}
