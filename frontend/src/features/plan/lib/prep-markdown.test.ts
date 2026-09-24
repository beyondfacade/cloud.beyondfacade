import { describe, expect, it } from "vitest";
import type { FinanceInput, FinanceResult, FundingCandidate } from "@/shared/api/types";
import { buildPrepMarkdown, buildQuestionsMarkdown, type PrepContext } from "./prep-markdown";
import { emptyDraft, recordCalculation, setCandidatesSeen, setProfile, setQuestions, type PlanDraft } from "./plan-draft";

const input: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_500_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.0405,
  expected_monthly_revenue: 8_000_000,
};
const result: FinanceResult = {
  capex: 50_000_000, monthly_fixed: 3_600_000, bep_revenue: 9_000_000, funding_gap: 6_600_000,
  reserve_months: 6, operating_reserve: 21_600_000, total_required_funds: 71_600_000,
  external_funding_need: 31_600_000, scenarios: [], stress: [],
};

const candidate: FundingCandidate = {
  program_id: "p1", source: "bizinfo", title: "2026년 소상공인 정책자금 융자사업",
  org: "중소벤처기업부", url: "https://example.test/1", apply_period: "상시",
  exec_org: null, field_category: "금융", field_subcategory: null, target_text: "소상공인",
  hashtags: null, apply_begin: null, deadline: null, summary: null, is_expired: false,
  why: "전국 · 소상공인 · 금융",
};

function ctx(overrides: Partial<PrepContext> = {}): PrepContext {
  let draft: PlanDraft = recordCalculation(emptyDraft({ region: "1168064000", industry: "cafe" }), input, result, ["key_money"]);
  draft = setProfile(draft, { business_registered: "unknown", planned_opening_date: "2026-11-01" });
  draft = setQuestions(draft, [{ text: "자기자본 외 3,160만 원을 어떤 경로로 나눠 조달할 수 있는지", basis: "조달 필요 31,600,000원 > 0", kind: "gap" }]);
  draft = setCandidatesSeen(draft, [candidate.title]);
  return { draft, regionName: "역삼1동", industryLabel: "카페", candidates: [candidate], caveats: ["예상 월매출은 이 동 카페 603곳의 평균입니다."], ...overrides };
}

describe("상담 준비자료 Markdown", () => {
  it("헤드라인은 자기자본 외 조달 필요다", () => {
    const md = buildPrepMarkdown(ctx());

    expect(md).toContain("**자기자본 외 조달 필요: 3,160만 원**");
  });

  it("숫자는 서버 결과 그대로 — 다시 계산하지 않는다", () => {
    const md = buildPrepMarkdown(ctx());

    expect(md).toContain("총 준비자금: 7,160만 원");
    expect(md).toContain("손익분기 월매출: 900만 원");
    expect(md).toContain("희망대출 반영 후 남는 부족액: 660만 원");
  });

  it("'모름'을 '아니오'로 바꾸지 않는다", () => {
    const md = buildPrepMarkdown(ctx());

    expect(md).toContain("사업자등록: 모름 — 상담에서 확인");
    expect(md).not.toContain("사업자등록: 등록 전");
  });

  it("미입력 0원 항목을 유효한 0원과 구분해 적는다", () => {
    const md = buildPrepMarkdown(ctx());

    expect(md).toContain("입력하지 않아 0원으로 계산한 항목: 권리금");
  });

  it("후보 공고는 원문 링크와 자격 미확정 고지를 함께 싣는다", () => {
    const md = buildPrepMarkdown(ctx());

    expect(md).toContain("[2026년 소상공인 정책자금 융자사업](https://example.test/1)");
    expect(md).toContain("자격 확정이 아니라 해당 가능성이 있는 공고입니다");
  });

  it("질문과 프리필 단서를 전부 싣는다", () => {
    const md = buildPrepMarkdown(ctx());

    expect(md).toContain("1. (조달) 자기자본 외 3,160만 원을");
    expect(md).toContain("예상 월매출은 이 동 카페 603곳의 평균입니다.");
  });

  it("확정·승인을 뜻하는 문구를 쓰지 않는다", () => {
    const md = buildPrepMarkdown(ctx());

    for (const banned of ["충분합니다", "승인", "신청 완료"]) {
      expect(md).not.toContain(banned);
    }
  });

  it("선택한 계산안이 없으면 빈 문자열이다 — 계산 전에는 준비자료가 없다", () => {
    const empty = { ...ctx(), draft: emptyDraft({ region: "r", industry: "cafe" }) };

    expect(buildPrepMarkdown(empty)).toBe("");
  });

  it("최초안·현재안이 둘 다 있으면 비교표와 변경 이유가 실린다", () => {
    const base = ctx();
    const changed = { ...base.draft.current ?? base.draft.baseline! };
    let draft = recordCalculation(base.draft, { ...input, monthly_rent: 1_000_000 }, { ...result, external_funding_need: 22_600_000 }, []);
    draft = { ...draft, change_reason: "월세를 250만에서 100만으로 낮춘 매물" };

    const md = buildPrepMarkdown({ ...base, draft });

    expect(changed).toBeDefined();
    expect(md).toContain("## 최초안과 현재안");
    expect(md).toContain("변경 이유: 월세를 250만에서 100만으로 낮춘 매물");
    expect(md).toContain("| 자기자본 외 조달 필요 | 3,160만 원 | 2,260만 원 |");
  });

  it("질문만 복사는 번호와 종류를 유지한다", () => {
    expect(buildQuestionsMarkdown(ctx().draft.questions)).toBe(
      "1. (조달) 자기자본 외 3,160만 원을 어떤 경로로 나눠 조달할 수 있는지\n",
    );
  });
});
