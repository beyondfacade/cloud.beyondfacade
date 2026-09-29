import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { reportFacts } from "../../lib/report-facts.fixture";
import { SignalBars } from "./signal-bars";

it("다섯 신호와 백분위 기준선 및 참고 표시를 그린다", () => {
  render(<SignalBars verdict={reportFacts().verdict} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(5);
  expect(screen.getByRole("meter", { name: "순유출" })).toHaveAttribute("aria-valuenow", "95");
  expect(screen.getByText("75")).toBeInTheDocument();
  expect(screen.getByText("90")).toBeInTheDocument();
  expect(within(screen.getByText("상권 축소").closest("li")!).getByText("참고")).toBeInTheDocument();
  expect(screen.getAllByText("미판정")).toHaveLength(2);
});
it("실패한 사실은 자료 없음이고 빈 신호는 다섯 미판정이다", () => {
  const { rerender } = render(<SignalBars verdict={{ available: false, reason: "없음" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
  const verdict = reportFacts().verdict;
  if ("available" in verdict) throw new Error("판정 없음");
  rerender(<SignalBars verdict={{ ...verdict, signals: [] }} />);
  expect(screen.getAllByText("미판정")).toHaveLength(5);
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
