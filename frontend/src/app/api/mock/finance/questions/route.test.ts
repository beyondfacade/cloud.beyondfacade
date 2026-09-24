import { expect, it } from "vitest";
import { POST } from "./route";

const input = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_500_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.0405,
  expected_monthly_revenue: 8_000_000,
};

function post(body: unknown) {
  return POST(new Request("http://test/api/mock/finance/questions", { method: "POST", body: JSON.stringify(body) }));
}

it("조달 필요·부족액이 남으면 조달 질문이 둘 나온다", async () => {
  const { questions } = await (await post({ input })).json();
  const gaps = questions.filter((q: { kind: string }) => q.kind === "gap");
  expect(gaps).toHaveLength(2);
  expect(gaps[0].text).toContain("자기자본 외");
});

it("계산 결과를 보내지 않아도 된다 — 서버가 input으로 다시 계산한다", async () => {
  const { questions } = await (await post({ input, unconfirmed: [], prefilled: [] })).json();
  expect(questions.length).toBeGreaterThan(0);
});

it("모른다고 둔 절차는 확인할 질문으로 남는다", async () => {
  const { questions } = await (await post({ input, profile: { business_registered: null, guarantee_status: "unknown", policy_confirmation_status: "issued" } })).json();
  const texts = questions.map((q: { text: string }) => q.text).join(" ");
  expect(texts).toContain("사업자등록 전인지 후인지");
  expect(texts).toContain("보증서 발급 절차");
  expect(texts).not.toContain("확인서가 필요한지");
});

it("후보 공고는 상위 3건까지만 질문이 된다", async () => {
  const { questions } = await (await post({ input, candidate_titles: ["가", "나", "다", "라"] })).json();
  const fromCandidates = questions.filter((q: { basis: string }) => q.basis === "후보 공고");
  expect(fromCandidates).toHaveLength(3);
});

it("input이 없으면 500이 아니라 422다", async () => {
  const res = await post({ profile: {} });
  expect(res.status).toBe(422);
  expect((await res.json()).error.code).toBe("INVALID_REQUEST");
});
