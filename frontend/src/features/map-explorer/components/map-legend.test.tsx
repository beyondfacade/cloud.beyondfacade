import { render, screen } from "@testing-library/react";
import { MapLegend, formatLegendValue } from "./map-legend";
import type { MetricColorClass } from "../lib/metric-color";

it("formatLegendValue: 비율 지표는 %(소수 1자리), 점포수는 정수", () => {
  expect(formatLegendValue("closure_rate", 0.034)).toBe("3.4%");
  expect(formatLegendValue("growth_rate", -0.021)).toBe("-2.1%"); // 음수 부호 그대로
  expect(formatLegendValue("store_count", 123.4)).toBe("123");
});

const CLASSES: MetricColorClass[] = [
  { color: "#ffffb2", from: 0.02, to: 0.05 },
  { color: "#b10026", from: 0.05, to: 0.18 },
];

it("구간 라벨과 '데이터 없음' 행을 목록으로 렌더링한다", () => {
  render(<MapLegend metric="closure_rate" classes={CLASSES} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(3); // 구간 2 + 데이터 없음 1
  expect(screen.getByText("2.0% ~ 5.0%")).toBeInTheDocument();
  expect(screen.getByText("데이터 없음")).toBeInTheDocument();
});

it("classes가 비어 있으면 아무것도 렌더링하지 않는다", () => {
  const { container } = render(<MapLegend metric="closure_rate" classes={[]} />);
  expect(container).toBeEmptyDOMElement();
});
