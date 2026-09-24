import { beforeEach, describe, expect, it } from "vitest";
import type { FinanceInput, FinanceResult, PlanQuestion } from "@/shared/api/types";
import { DRAFT_KEY, emptyDraft, loadDraft, recordCalculation, saveDraft, selectPlan, selectedPlan, setCandidatesSeen, setProfile, setQuestions, withScope } from "./plan-draft";

const input: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_500_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.048,
  expected_monthly_revenue: 8_000_000,
};
const result: FinanceResult = {
  capex: 50_000_000, monthly_fixed: 3_600_000, bep_revenue: 9_000_000, funding_gap: 6_600_000,
  reserve_months: 6, operating_reserve: 21_600_000, total_required_funds: 71_600_000, external_funding_need: 31_600_000,
  scenarios: [], stress: [],
};
const scope = { region: "1168064000", industry: "cafe" };

describe("계획 초안", () => {
  beforeEach(() => sessionStorage.clear());

  it("첫 계산은 최초안으로 고정되고 두 번째부터 현재안이 갱신된다", () => {
    let draft = recordCalculation(emptyDraft(scope), input, result, ["deposit"]);
    expect(draft.baseline?.result.external_funding_need).toBe(31_600_000);
    expect(draft.selected).toBe("baseline");
    draft = recordCalculation(draft, { ...input, monthly_rent: 1_000_000 }, { ...result, external_funding_need: 22_600_000 });
    expect(draft.baseline?.input.monthly_rent).toBe(2_500_000); // 최초안은 그대로
    expect(draft.current?.result.external_funding_need).toBe(22_600_000);
    expect(draft.selected).toBe("current");
  });

  it("없는 계산안은 선택되지 않는다", () => {
    const draft = recordCalculation(emptyDraft(scope), input, result);
    expect(selectPlan(draft, "current").selected).toBe("baseline");
    expect(selectedPlan(draft)?.result.bep_revenue).toBe(9_000_000);
  });

  it("지역·업종이 바뀌면 결과를 비우되 변경 이유는 남긴다", () => {
    const draft = { ...recordCalculation(emptyDraft(scope), input, result), change_reason: "월세를 낮췄다" };
    const moved = withScope(draft, { region: "1168065000", industry: "cafe" });
    expect(moved.baseline).toBeNull();
    expect(moved.change_reason).toBe("월세를 낮췄다");
    expect(withScope(draft, scope)).toBe(draft);
  });

  it("sessionStorage 왕복 — 저장한 초안이 그대로 복원된다", () => {
    const draft = recordCalculation(emptyDraft(scope), input, result, ["deposit"]);
    saveDraft(draft);
    expect(sessionStorage.getItem(DRAFT_KEY)).not.toBeNull();
    expect(loadDraft()).toEqual(draft);
  });

  it("버전이 다르거나 비율이 어긋난 저장값은 복원하지 않는다", () => {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ ...emptyDraft(scope), version: 0 }));
    expect(loadDraft()).toBeNull();
    const broken = recordCalculation(emptyDraft(scope), { ...input, cost_ratio: 0.98 }, result);
    saveDraft(broken);
    expect(loadDraft()).toBeNull();
  });
});

describe("v2 — 창업 단계·질문·본 후보", () => {
  it("빈 초안의 창업 단계는 전부 미확인이다 — 0·아니오로 바꾸지 않는다", () => {
    const draft = emptyDraft({ region: "1168064000", industry: "cafe" });

    expect(draft.profile.business_registered).toBeNull();
    expect(draft.profile.guarantee_status).toBe("unknown");
    expect(draft.questions).toEqual([]);
  });

  it("'모른다'(unknown)와 '아직 묻지 않음'(null)을 구분해 보관한다", () => {
    const draft = setProfile(emptyDraft({ region: "r", industry: "cafe" }), {
      business_registered: "unknown",
    });

    expect(draft.profile.business_registered).toBe("unknown");
  });

  it("질문 편집본이 왕복에서 살아남는다", () => {
    const q: PlanQuestion[] = [{ text: "고친 질문", basis: "조달 필요 > 0", kind: "gap" }];
    const draft = setQuestions(emptyDraft({ region: "r", industry: "cafe" }), q);

    saveDraft(draft);

    expect(loadDraft()?.questions).toEqual(q);
  });

  it("동네가 바뀌면 후보·질문은 버리고 사람이 쓴 것은 남긴다", () => {
    let draft = setQuestions(emptyDraft({ region: "r1", industry: "cafe" }), [
      { text: "q", basis: "b", kind: "gap" },
    ]);
    draft = setCandidatesSeen(draft, ["공고 A"]);
    draft = setProfile({ ...draft, change_reason: "월세를 낮춘 매물" }, { business_registered: true });

    const moved = withScope(draft, { region: "r2", industry: "cafe" });

    expect(moved.questions).toEqual([]);
    expect(moved.candidates_seen).toEqual([]);
    expect(moved.change_reason).toBe("월세를 낮춘 매물");
    expect(moved.profile.business_registered).toBe(true);
  });

  it("구버전(v1) 초안은 되살리지 않는다 — 구조가 달라 화면이 undefined를 만진다", () => {
    sessionStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({ version: 1, region: "r", industry: "cafe", baseline: null, current: null, selected: null, change_reason: "" }),
    );

    expect(loadDraft()).toBeNull();
  });
});
