import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { reportFacts } from "../../lib/report-facts.fixture";
import { AlternativesCards } from "./alternatives-cards";

it.each([
  ["red", "비추천", "var(--danger)"],
  ["orange", "조건부", "var(--warn)"],
  ["clear", "경고 없음", "var(--text-secondary)"],
  ["insufficient", "판정 보류", "var(--border)"],
] as const)("대안의 %s 판정을 해당 색상의 배지로 표시한다", (code, label, color) => {
  const alternatives = reportFacts().alternatives;
  if ("available" in alternatives) throw new Error("대안 없음");
  render(<AlternativesCards alternatives={{ ...alternatives,
    industries: [{ ...alternatives.industries[0], verdict_code: code }],
    regions: [{ ...alternatives.regions[0], verdict_code: code }],
  }} />);
  for (const badge of screen.getAllByText(label)) {
    expect(badge).toHaveStyle({ color });
    expect(badge.style.borderColor).toBe(color);
  }
});

it("두 축에 이름과 판정 라벨을 최대 세 개씩 표시한다", () => {
  const alternatives = reportFacts().alternatives;
  if ("available" in alternatives) throw new Error("대안 없음");
  render(<AlternativesCards alternatives={{ ...alternatives,
    industries: Array.from({ length: 4 }, (_, i) => ({ ...alternatives.industries[0], industry_id: `${i}`, industry_name: `업종${i}` })),
    regions: Array.from({ length: 4 }, (_, i) => ({ ...alternatives.regions[0], region_code: `${i}`, region_name: `동네${i}` })),
  }} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(6);
  expect(screen.getAllByText("경고 없음")).toHaveLength(3);
  expect(screen.getAllByText("조건부")).toHaveLength(3);
  expect(screen.queryByText("업종3")).toBeNull();
  expect(screen.queryByText("동네3")).toBeNull();
});
it("빈 축은 대안 없음이고 실패한 사실은 자료 없음이다", () => {
  const { rerender } = render(<AlternativesCards alternatives={{ region_code: "1", industry_id: "cafe", neighborhood_type: null, industries: [], regions: [] }} />);
  expect(screen.getAllByText("대안 없음")).toHaveLength(2);
  rerender(<AlternativesCards alternatives={{ available: false, reason: "없음" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
});
