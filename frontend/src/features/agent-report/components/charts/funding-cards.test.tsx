import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { FundingCards } from "./funding-cards";

it.each([
  [null, "업종에 맞는 지원사업", "업종에 맞는 지원사업"],
  ["", "업종에 맞는 지원사업", "업종에 맞는 지원사업"],
  ["지원 요약", "추천 이유", "지원 요약"],
  [null, null, "요약 없음"],
])("요약 %s와 추천 이유 %s에 따라 설명과 툴팁을 표시한다", (summary, why, expected) => {
  render(<FundingCards candidates={[{ title: "공고", summary, why }]} />);
  expect(screen.getByText(expected)).toHaveAttribute("title", expected);
});

it("공고 카드에 기업마당 출처를 표시한다", () => {
  render(<FundingCards candidates={[{ title: "공고", summary: "지원 요약" }]} />);
  expect(screen.getByText("출처: 기업마당")).toBeInTheDocument();
});

it("후보 다섯 개까지 기관 요약 대상과 안전한 원문 링크를 표시한다", () => {
  render(<FundingCards candidates={Array.from({ length: 6 }, (_, i) => ({ id: `${i}`, title: `공고${i}`, org: "서울시", summary: "지원 요약", target: "소상공인", url: `https://example.com/${i}` }))} />);
  expect(screen.getAllByRole("link", { name: "원문" })).toHaveLength(5);
  expect(screen.getAllByRole("link")[0]).toHaveAttribute("rel", "noopener");
  expect(screen.getAllByText("서울시")).toHaveLength(5);
  expect(screen.getAllByText("지원 요약")).toHaveLength(5);
  expect(screen.getAllByText("대상: 소상공인")).toHaveLength(5);
  expect(screen.queryByText("공고5")).toBeNull();
});
it("빈 후보와 실패는 자료 없음이며 누락 필드와 위험한 링크에 방어한다", () => {
  const { rerender } = render(<FundingCards candidates={[]} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
  rerender(<FundingCards candidates={{ available: false, reason: "실패" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
  rerender(<FundingCards candidates={[{ title: "공고", target: "예비 창업자", url: "javascript:alert(1)" }]} />);
  expect(screen.getByText("대상: 예비 창업자")).toBeInTheDocument();
  expect(screen.queryByRole("link")).toBeNull();
});

it.each([undefined, null, ""])("대상이 %s이면 대상 줄을 생략한다", (target) => {
  render(<FundingCards candidates={[{ title: "공고", target, target_text: "구형 대상", field_category: "창업", apply_period: "상시" }]} />);
  expect(screen.queryByText(/^대상:/)).toBeNull();
  expect(screen.queryByText(/자료 없음/)).toBeNull();
});
