import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FinanceInput, FinanceResult } from "@/shared/api/types";
import { emptyDraft, recordCalculation, setQuestions } from "../lib/plan-draft";
import { PrepSheet } from "./prep-sheet";

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

function draftWithPlan() {
  return setQuestions(
    recordCalculation(emptyDraft({ region: "1168064000", industry: "cafe" }), input, result, []),
    [{ text: "조달 경로를 어떻게 나눌지", basis: "조달 필요 > 0", kind: "gap" }],
  );
}

describe("상담 준비자료", () => {
  it("계산 전에는 준비자료를 만들지 않는다", () => {
    render(<PrepSheet draft={emptyDraft({ region: "r", industry: "cafe" })} regionName="역삼1동" industryLabel="카페" candidates={[]} caveats={[]} />);

    expect(screen.getByText("상담할 안을 고르면 준비자료가 만들어집니다.")).toBeInTheDocument();
  });

  it("헤드라인과 단서가 본문에 실린다", () => {
    render(<PrepSheet draft={draftWithPlan()} regionName="역삼1동" industryLabel="카페" candidates={[]} caveats={["월세는 권역 평균입니다."]} />);

    const body = screen.getByText(/창업자금 상담 준비자료/).textContent ?? "";
    expect(body).toContain("자기자본 외 조달 필요: 3,160만 원");
    expect(body).toContain("월세는 권역 평균입니다.");
  });

  it("복사 버튼은 Markdown 전체를 클립보드에 넣는다", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<PrepSheet draft={draftWithPlan()} regionName="역삼1동" industryLabel="카페" candidates={[]} caveats={[]} />);

    await userEvent.click(screen.getByRole("button", { name: "Markdown 복사" }));

    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("# 창업자금 상담 준비자료"));
    expect(screen.getByRole("button", { name: "복사했습니다" })).toBeInTheDocument();
  });

  it("은행에 보내는 것처럼 보이는 버튼을 두지 않는다", () => {
    render(<PrepSheet draft={draftWithPlan()} regionName="역삼1동" industryLabel="카페" candidates={[]} caveats={[]} />);

    for (const name of [/전송/, /제출/, /신청/, /예약/]) {
      expect(screen.queryByRole("button", { name })).toBeNull();
    }
  });
});

describe("금지 문구", () => {
  // 은행 전송·예약·신청을 하지 않으므로 확정·승인을 뜻하는 말을 화면에 두지 않는다(설계서 §5).
  // 규칙을 설명하는 주석은 위반이 아니라서 주석을 걷어낸 뒤 본다.
  const BANNED = ["충분합니다", "신청 완료", "승인되었"];
  const stripComments = (source: string) =>
    source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

  it("plan feature의 화면 문구에 확정·승인 표현이 없다", () => {
    const root = path.join(process.cwd(), "src/features/plan");
    const offenders: string[] = [];

    const walk = (dir: string) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (/\.tsx?$/.test(entry.name) && !entry.name.includes(".test.")) {
          const text = stripComments(readFileSync(full, "utf-8"));
          for (const phrase of BANNED) {
            if (text.includes(phrase)) offenders.push(`${entry.name}: ${phrase}`);
          }
        }
      }
    };
    walk(root);

    expect(offenders).toEqual([]);
  });

  it("주석에 적힌 규칙 자체는 위반으로 세지 않는다", () => {
    const source = readFileSync(path.join(process.cwd(), "src/features/plan/components/result-figures.tsx"), "utf-8");

    expect(source).toContain("충분합니다"); // 규칙을 적어둔 주석이 실제로 있다
    expect(stripComments(source)).not.toContain("충분합니다");
  });
});
