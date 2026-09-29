"use client";

import { ApiError } from "@/shared/api/client";
import { INDUSTRIES, industryLabel } from "@/shared/industries";
import { isVerdictIndustry, verdictExclusionNotice } from "@/shared/verdict";
import { VerdictCard } from "@/shared/ui/verdict-card";
import { useVerdict } from "../hooks/use-verdict";
import { VerdictAlternatives } from "./verdict-alternatives";

/** 404(판정 없음·판정 대상 아님)는 카드를 그리지 않는다 — 학원·어린이집·배치 전 조합의 정상 동작. */
function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && (error.code === "VERDICT_NOT_FOUND" || error.code === "INDUSTRY_NOT_FOUND");
}

interface VerdictSectionProps {
  regionCode: string;
  industry: string;
}

export function VerdictSection({ regionCode, industry }: VerdictSectionProps) {
  const query = useVerdict(regionCode, industry);

  if (!isVerdictIndustry(industry)) {
    // select 업종인데 판정 제외면 안내 한 줄(설계서 §13), select 밖 업종(학원·어린이집)은 아무것도 그리지 않는다
    return (INDUSTRIES as readonly string[]).includes(industry)
      ? <p className="mt-3 text-xs text-[var(--text-secondary)]">{verdictExclusionNotice(industry)}</p>
      : null;
  }
  if (query.isPending) {
    return <div className="mt-4 h-16 rounded-lg bg-[var(--bg-raised)]" aria-hidden />;
  }
  if (query.isError) {
    if (isNotFound(query.error)) return null;
    return (
      <p role="alert" className="mt-4 text-xs text-[var(--danger)]">
        판정을 불러오지 못했습니다.
      </p>
    );
  }

  const verdict = query.data;
  return (
    <>
      <VerdictCard verdict={verdict} industryLabel={industryLabel(industry)} />
      {verdict.verdict_code !== "clear" && <VerdictAlternatives regionCode={regionCode} industry={industry} />}
    </>
  );
}
