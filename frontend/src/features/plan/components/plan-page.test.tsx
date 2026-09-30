import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { FinanceResult } from "@/shared/api/types";
import { PlanPage } from "./plan-page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams({ region: "1168064000", industry: "cafe" }),
}));

const RESULT: FinanceResult = {
  capex: 50_000_000, monthly_fixed: 3_600_000, bep_revenue: 9_000_000, funding_gap: 0,
  reserve_months: 6, operating_reserve: 21_600_000, total_required_funds: 71_600_000, external_funding_need: 31_600_000,
  scenarios: [], stress: [],
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.includes("/finance/simulate")) return Response.json(RESULT);
    return new Response("{}", { status: 500 });
  }));
});
afterEach(() => vi.unstubAllGlobals());

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><PlanPage /></QueryClientProvider>);
}

it("화면에 다시 들어오면 이전 계산 결과 없이 빈 계획서로 시작한다", async () => {
  const first = renderPage();
  await userEvent.click(screen.getByRole("button", { name: "계산하기" }));
  expect((await screen.findAllByText("자기자본 외 조달 필요")).length).toBeGreaterThan(0);
  first.unmount();

  renderPage();
  expect(screen.queryAllByText("자기자본 외 조달 필요")).toHaveLength(0);
  expect(screen.getByText("나의 자금 계획서")).toBeInTheDocument();
});
