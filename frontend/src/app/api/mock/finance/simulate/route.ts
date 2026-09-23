import type { FinanceInput } from "@/shared/api/types";
import { simulate } from "@/features/plan/lib/finance-engine";

const AMOUNTS: (keyof FinanceInput)[] = ["deposit", "key_money", "interior_cost", "equipment_cost", "monthly_rent", "monthly_payroll", "monthly_insurance", "equity", "desired_loan", "expected_monthly_revenue"];
const RATIOS: (keyof FinanceInput)[] = ["cost_ratio", "fee_ratio", "loan_rate"];

/** 실 API(FastAPI)의 검증 규칙과 같이 422로 답한다 — 금액 ≥ 0, 비율 0 ≤ r < 1, 원가율+수수료율 < 1. */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as Partial<FinanceInput> | null;
  const problems: string[] = [];
  for (const f of AMOUNTS) if (!Number.isFinite(body?.[f]) || (body![f] as number) < 0) problems.push(f);
  for (const f of RATIOS) if (!Number.isFinite(body?.[f]) || (body![f] as number) < 0 || (body![f] as number) >= 1) problems.push(f);
  if (problems.length === 0 && (body!.cost_ratio! + body!.fee_ratio!) >= 1) problems.push("cost_ratio + fee_ratio 는 1 미만이어야 합니다");
  if (problems.length > 0) return Response.json({ detail: problems.map((p) => ({ loc: ["body", p], msg: "invalid", type: "value_error" })) }, { status: 422 });
  return Response.json(simulate(body as FinanceInput));
}
