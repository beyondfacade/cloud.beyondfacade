import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { reportFacts } from "../../lib/report-facts.fixture";
import { MetricTrend } from "./metric-trend";

it("연도별 점포수와 두 비율을 단위를 나눠 그리고 값 툴팁을 제공한다", () => {
  const { container } = render(<MetricTrend history={reportFacts().metrics_history} />);
  expect(screen.getByRole("img", { name: "점포수 추세" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "폐업률·성장률 추세" })).toBeInTheDocument();
  expect(screen.getAllByText("2025")).toHaveLength(2);
  expect(container.querySelectorAll("polyline")).toHaveLength(3);
  expect(screen.getByText("2025년 점포수: 100개", { selector: "title" })).toBeInTheDocument();
  expect(screen.getByText("2025년 성장률: -2.0%", { selector: "title" })).toBeInTheDocument();
});
it("두 연도 미만은 추세 자료 없음이고 실패한 사실은 자료 없음이다", () => {
  const { rerender } = render(<MetricTrend history={[]} />);
  expect(screen.getByText("추세 자료 없음")).toBeInTheDocument();
  const history = reportFacts().metrics_history;
  if (!Array.isArray(history)) throw new Error("이력 없음");
  rerender(<MetricTrend history={history.slice(0, 1)} />);
  expect(screen.getByText("추세 자료 없음")).toBeInTheDocument();
  rerender(<MetricTrend history={{ available: false, reason: "없음" }} />);
  expect(screen.getByText("자료 없음")).toBeInTheDocument();
});
