import type { IntentResult } from "@/shared/api/types";

/** 관문 결과 → 지도 착지 URL. 없는 값은 생략한다. 진단 문장은 싣지 않는다 — 패널이 같은 데이터를 다시 읽는다. */
export function intentToUrl(r: Pick<IntentResult, "region_code" | "industry_id" | "budget_krw">): string {
  const p = new URLSearchParams();
  if (r.region_code) p.set("region", r.region_code);
  if (r.industry_id) p.set("industry", r.industry_id);
  if (r.budget_krw) p.set("budget", String(r.budget_krw));
  const q = p.toString();
  return q ? `/map?${q}` : "/map";
}

/** A유형(동+업종)일 때만 자금 계획 링크. 관문의 예산을 그대로 싣는다 — /plan이 자기자본으로 프리필한다. */
export function planUrl(r: Pick<IntentResult, "region_code" | "industry_id" | "budget_krw">): string | null {
  if (!r.region_code || !r.industry_id) return null;
  const p = new URLSearchParams({ region: r.region_code, industry: r.industry_id });
  if (r.budget_krw) p.set("budget", String(r.budget_krw));
  return `/plan?${p.toString()}`;
}
