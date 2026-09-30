import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { eventAnalogs } from "../../lib/report-facts.fixture";
import { AnalogCases } from "./analog-cases";

it("진행 중 이벤트와 지난 사례를 이름·기간·유형과 함께 보여 준다", () => {
  render(<AnalogCases analogs={eventAnalogs()} />);
  const current = screen.getByRole("article", { name: "최저임금 인상 — 2026년" });
  expect(within(current).getByText("진행 중")).toBeInTheDocument();
  const covid = screen.getByRole("article", { name: "코로나19 국내 유행과 방역 조치" });
  expect(within(covid).getByText("2020-01-20 ~ 2022-04-17 · 약 27개월")).toBeInTheDocument();
  expect(within(covid).queryByText("진행 중")).toBeNull();
  expect(screen.getByText("감염병·방역 · 질문 속 상황")).toBeInTheDocument();
  expect(screen.getByText("최저임금 · 진행 중 이벤트")).toBeInTheDocument();
});

it("창마다 평소 대비 변동폭 막대를 그리고 내 업종을 표시한다", () => {
  render(<AnalogCases analogs={eventAnalogs()} />);
  const covid = screen.getByRole("article", { name: "코로나19 국내 유행과 방역 조치" });
  const immediate = within(covid).getByRole("group", { name: "직후 3개월 2020-01~2020-03" });
  const rows = within(immediate).getAllByRole("listitem");
  // 강세 → 약세 순, 내 업종(카페)은 목록에 한 번만
  expect(rows.map((row) => row.getAttribute("aria-label"))).toEqual([
    "중식 +0.8%p", "호프·주점 +0.7%p", "PC방 -0.6%p", "카페 -0.8%p (내 업종)",
  ]);
  expect(within(rows[0]).getByTestId("bar")).toHaveStyle({ backgroundColor: "var(--ok)" });
  expect(within(rows[3]).getByTestId("bar")).toHaveStyle({ backgroundColor: "var(--danger)" });
  expect(within(covid).getByRole("group", { name: "1년 차 마지막 3개월 2020-10~2020-12" })).toBeInTheDocument();
});

it("유형별 사례 종합으로 내 업종 추세·지속 기간·거듭 강세/약세 업종을 보여 준다", () => {
  render(<AnalogCases analogs={eventAnalogs()} />);
  const outlook = screen.getByRole("article", { name: "감염병·방역 사례 종합" });
  expect(outlook).toHaveTextContent("사례 2건 — 내 업종은 평소보다 약했어요");
  expect(outlook).toHaveTextContent("보통 약 17개월 이어짐");
  const strong = within(outlook).getByRole("list", { name: "거듭 강세" });
  expect(within(strong).getByText("양식")).toHaveStyle({ color: "var(--ok)" });
  expect(within(strong).getByText("중식")).toBeInTheDocument();
  const weak = within(outlook).getByRole("list", { name: "거듭 약세" });
  expect(within(weak).getByText("PC방")).toHaveStyle({ color: "var(--danger)" });
});

it("해석 주의사항을 함께 적는다", () => {
  render(<AnalogCases analogs={eventAnalogs()} />);
  expect(screen.getByText(/12월에는 행정 정리로 폐업이 몰린다/)).toBeInTheDocument();
});

it("비교할 이벤트가 없으면 그렇게 쓰고, 실패한 사실은 자료 없음이다", () => {
  const { rerender } = render(<AnalogCases analogs={{ ...eventAnalogs(), categories: [], current_events: [], analogs: [] }} />);
  expect(screen.getByText("비교할 이벤트가 없습니다.")).toBeInTheDocument();
  rerender(<AnalogCases analogs={{ available: false, reason: "없음" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
  rerender(<AnalogCases analogs={undefined} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
});
