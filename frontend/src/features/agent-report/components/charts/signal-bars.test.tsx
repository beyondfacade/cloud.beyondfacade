import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { reportFacts } from "../../lib/report-facts.fixture";
import { SignalBars } from "./signal-bars";

it("등급 문구가 있으면 백분위 대신 표시한다", () => {
  const verdict = reportFacts().verdict;
  if ("available" in verdict) throw new Error("판정 없음");
  render(<SignalBars verdict={{ ...verdict, signals: [{ ...verdict.signals[0], band_label: "순유출 매우 많은 편" }] }} />);
  expect(screen.getByText("순유출 매우 많은 편")).toBeInTheDocument();
  expect(screen.queryByText("95백분위")).not.toBeInTheDocument();
  expect(screen.getByRole("meter").firstElementChild).toHaveStyle({ width: "95%", backgroundColor: "var(--danger)" });
});

it.each([undefined, null])("등급 문구가 %s이면 기존 백분위 표기를 유지한다", (band_label) => {
  const verdict = reportFacts().verdict;
  if ("available" in verdict) throw new Error("판정 없음");
  render(<SignalBars verdict={{ ...verdict, signals: [{ ...verdict.signals[0], band_label }] }} />);
  expect(screen.getByText("95백분위")).toBeInTheDocument();
});

it("신호 백분위와 기준선을 이름 있는 그룹으로 노출한다", () => {
  render(<SignalBars verdict={reportFacts().verdict} />);
  const group = screen.getByRole("group", { name: "신호 백분위" });
  const thresholds = within(group).getByRole("group", { name: "백분위 기준선" });
  expect(within(thresholds).getByText("75")).toBeInTheDocument();
  expect(within(thresholds).getByText("90")).toBeInTheDocument();
});

it("네 신호와 백분위 기준선을 그린다", () => {
  render(<SignalBars verdict={reportFacts().verdict} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(4);
  expect(screen.getByRole("meter", { name: "순유출" })).toHaveAttribute("aria-valuenow", "95");
  expect(screen.getByText("75")).toBeInTheDocument();
  expect(screen.getByText("90")).toBeInTheDocument();
  expect(screen.getAllByText("미판정")).toHaveLength(1);
});
it("인허가 판정 응답에 없는 업종 특화 신호는 그리지 않는다", () => {
  render(<SignalBars verdict={reportFacts().verdict} />);
  expect(screen.queryByText("폐업률")).not.toBeInTheDocument();
  expect(screen.queryByText("담배권 빈자리")).not.toBeInTheDocument();
  expect(screen.queryByText("사무소당 거래")).not.toBeInTheDocument();
});

it("실패한 사실은 자료 없음이고 빈 신호는 막대를 그리지 않는다", () => {
  const { rerender } = render(<SignalBars verdict={{ available: false, reason: "없음" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
  const verdict = reportFacts().verdict;
  if ("available" in verdict) throw new Error("판정 없음");
  rerender(<SignalBars verdict={{ ...verdict, signals: [] }} />);
  expect(screen.queryAllByRole("listitem")).toHaveLength(0);
});

it("백분위는 영과 백 경계 안에 표시하고 신호 레벨별 토큰을 쓴다", () => {
  const verdict = reportFacts().verdict;
  if ("available" in verdict) throw new Error("판정 없음");
  render(<SignalBars verdict={{ ...verdict, signals: verdict.signals.map((signal, i) => ({ ...signal, percentile: i === 0 ? 110 : i === 1 ? -10 : signal.percentile })) }} />);
  const strong = screen.getByRole("meter", { name: "순유출" });
  expect(strong).toHaveAttribute("aria-valuenow", "100");
  expect(strong.firstElementChild).toHaveStyle({ backgroundColor: "var(--danger)" });
  const on = screen.getByRole("meter", { name: "생존 절벽" });
  expect(on).toHaveAttribute("aria-valuenow", "0");
  expect(on.firstElementChild).toHaveStyle({ backgroundColor: "var(--warn)" });
  expect(screen.getByRole("meter", { name: "조기 폐업" }).firstElementChild).toHaveStyle({ backgroundColor: "var(--text-secondary)" });
});
