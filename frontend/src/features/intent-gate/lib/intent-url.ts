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
