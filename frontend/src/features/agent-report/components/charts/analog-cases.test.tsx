import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { eventAnalogs } from "../../lib/report-facts.fixture";
import { AnalogCases } from "./analog-cases";

it("진행 중 이벤트와 지난 사례를 이름·기간·유형과 함께 보여 준다", () => {
  render(<AnalogCases analogs={eventAnalogs()} />);
  const current = screen.getByRole("article", { name: "최저임금 인상 — 2026년" });
  expect(within(current).getByText("진행 중")).toBeInTheDocument();
  // 최저임금은 그 해 4분기만 본다 — 아직 2분기만 끝났다
  expect(within(current).getByText("내 업종 2분기 중 약세 0 · 강세 2 · 비교 기간 4분기 중 2분기 지남")).toBeInTheDocument();
  expect(within(current).getAllByRole("cell")).toHaveLength(2);
  const covid = screen.getByRole("article", { name: "코로나19 국내 유행과 방역 조치" });
  expect(within(covid).getByText("2020-01-20 ~ 2022-04-17 · 약 27개월")).toBeInTheDocument();
  expect(within(covid).queryByText("진행 중")).toBeNull();
  expect(screen.getByText("감염병·방역 · 질문 속 상황")).toBeInTheDocument();
  expect(screen.getByText("최저임금 · 진행 중 이벤트")).toBeInTheDocument();
});

it("사례마다 업종별 12분기 흐름을 강세·약세 색 칸으로 그리고 내 업종을 표시한다", () => {
  render(<AnalogCases analogs={eventAnalogs()} />);
  const covid = screen.getByRole("article", { name: "코로나19 국내 유행과 방역 조치" });
  expect(within(covid).getByText("내 업종 12분기 중 약세 12 · 강세 0 · 처음부터 12분기 연속 약세")).toBeInTheDocument();
  const grid = within(covid).getByRole("table", { name: "코로나19 국내 유행과 방역 조치 분기별 변동폭" });
  expect(within(grid).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["업종", "1년 차", "2년 차", "3년 차"]);
  const [cafe, western, pcBang] = within(grid).getAllByRole("row").slice(1);
  expect(within(cafe).getByRole("rowheader")).toHaveTextContent("카페 (내 업종)");
  expect(within(western).getByRole("rowheader")).toHaveTextContent("양식 (거듭 강세)");
  expect(within(pcBang).getByRole("rowheader")).toHaveTextContent("PC방 (거듭 약세)");
  const cafeCells = within(cafe).getAllByRole("cell");
  expect(cafeCells).toHaveLength(12);
  expect(cafeCells[0]).toHaveTextContent("1년 차 1분기 -0.8%p");
  expect(cafeCells.every((cell) => cell.dataset.tone === "weak")).toBe(true);
  const westernCells = within(western).getAllByRole("cell");
  expect(westernCells[4]).toHaveAttribute("data-tone", "strong");
  expect(westernCells[7]).toHaveAttribute("data-tone", "flat"); // -0.2는 평소와 비슷
  expect(westernCells[11]).toHaveTextContent("3년 차 4분기 자료 없음");
});

it("분기에 겹친 다른 정책을 함께 적고, 끝난 분기가 없으면 그렇게 쓴다", () => {
  const data = eventAnalogs();
  const { rerender } = render(<AnalogCases analogs={data} />);
  const overlaps = screen.getByRole("list", { name: "겹친 이벤트" });
  expect(within(overlaps).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "1년 차 2분기 — 1차 긴급재난지원금 지급", "2년 차 4분기 — 소상공인 손실보상제 시행",
  ]);
  const fresh = { ...data.current_events[0], quarters: [], series: [] };
  rerender(<AnalogCases analogs={{ ...data, current_events: [fresh], analogs: [] }} />);
  expect(screen.getByText("아직 끝난 분기가 없습니다.")).toBeInTheDocument();
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

it("비교하지 않은 유형은 질문에 넣을 예시 단어로 안내하고, 없으면 안내하지 않는다", () => {
  const { rerender } = render(<AnalogCases analogs={eventAnalogs()} />);
  expect(screen.getByRole("note", { name: "다른 상황 비교 안내" })).toHaveTextContent(
    "근로시간, 지원금·보상 사례는 질문에 \"52시간\", \"지원금\" 같은 단어를 넣으면 함께 비교합니다.",
  );
  rerender(<AnalogCases analogs={{ ...eventAnalogs(), hints: [] }} />);
  expect(screen.queryByRole("note", { name: "다른 상황 비교 안내" })).toBeNull();
});

it("비교할 이벤트가 없으면 그렇게 쓰고, 실패한 사실은 자료 없음이다", () => {
  const { rerender } = render(<AnalogCases analogs={{ ...eventAnalogs(), categories: [], current_events: [], analogs: [] }} />);
  expect(screen.getByText("비교할 이벤트가 없습니다.")).toBeInTheDocument();
  rerender(<AnalogCases analogs={{ available: false, reason: "없음" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
  rerender(<AnalogCases analogs={undefined} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
});
