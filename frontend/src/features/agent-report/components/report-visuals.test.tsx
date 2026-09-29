import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { reportFacts } from "../lib/report-facts.fixture";
import { ReportVisuals } from "./report-visuals";

it("업종 공통 충격에만 전 업종 공통 표시를 붙인다", () => {
  render(<ReportVisuals section="reasons" facts={{ ...reportFacts(), shocks: [
    { event_id: "common", name: "금리 상승", industry_specific: false },
    { event_id: "specific", name: "원두 가격 상승", industry_specific: true },
    { event_id: "unknown", name: "미분류 충격" },
  ] }} />);
  const items = within(screen.getByRole("region", { name: "외부 충격" })).getAllByRole("listitem");
  expect(within(items[0]).getByText("전 업종 공통")).toBeInTheDocument();
  expect(within(items[1]).queryByText("전 업종 공통")).toBeNull();
  expect(within(items[2]).queryByText("전 업종 공통")).toBeNull();
});

it.each([
  [undefined, "2026-09-01"],
  ["2026-09-30", "2026-09-01~2026-09-30"],
])("충격 시작일과 종료일 %s를 날짜로 표시한다", (end_date, expected) => {
  render(<ReportVisuals section="reasons" facts={{ ...reportFacts(), shocks: [
    { event_id: "s1", name: "원두 가격 상승", start_date: "2026-09-01", end_date, industry_specific: true },
  ] }} />);
  expect(within(screen.getByRole("region", { name: "외부 충격" })).getByText(expected)).toBeInTheDocument();
});
