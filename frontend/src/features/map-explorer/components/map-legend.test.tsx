import { render, screen } from "@testing-library/react";
import { MapLegend, formatLegendValue } from "./map-legend";
import type { MetricColorClass } from "../lib/metric-color";

it("formatLegendValue: 비율 지표는 %(소수 1자리), 점포수는 정수, 영업 지속은 개월", () => {
  expect(formatLegendValue("closure_rate", 0.034)).toBe("3.4%");
  expect(formatLegendValue("growth_rate", -0.021)).toBe("-2.1%"); // 음수 부호 그대로
  expect(formatLegendValue("store_count", 123.4)).toBe("123");
  expect(formatLegendValue("operating_months", 117.4)).toBe("117개월");
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

it("동 단위 지표에는 업종과 무관하다는 단서를 붙인다", () => {
  // 업종을 바꿔도 색이 안 변하는 이유를 범례가 말해준다
  render(<MapLegend metric="operating_months" classes={CLASSES} />);
  expect(screen.getByText("업종 구분 없는 동 전체 평균")).toBeInTheDocument();
});

it("업종 지표에는 그 단서를 붙이지 않는다", () => {
  render(<MapLegend metric="closure_rate" classes={CLASSES} />);
  expect(screen.queryByText("업종 구분 없는 동 전체 평균")).toBeNull();
});
