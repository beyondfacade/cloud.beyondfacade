import { render, screen } from "@testing-library/react";
import { MapLegend, formatLegendValue } from "./map-legend";
import type { MetricColorClass } from "../lib/metric-color";

it("formatLegendValue: 비율은 %(소수 1자리), 점포수는 정수, 영업 지속은 개월, 심야 체류는 소수 2자리", () => {
  expect(formatLegendValue("closure_rate", 0.034)).toBe("3.4%");
  expect(formatLegendValue("growth_rate", -0.021)).toBe("-2.1%"); // 음수 부호 그대로
  expect(formatLegendValue("store_count", 123.4)).toBe("123");
  expect(formatLegendValue("operating_months", 117.4)).toBe("117개월");
  expect(formatLegendValue("night_index", 1.0737)).toBe("1.07");
  expect(formatLegendValue("fnb_share", 0.2429)).toBe("24.3%");
});

const CLASSES: MetricColorClass[] = [
  { color: "#ffffb2", from: 0.02, to: 0.05 },
  { color: "#b10026", from: 0.05, to: 0.18 },
];

it("구간 라벨과 '데이터 없음' 행을 목록으로 렌더링한다", () => {
  render(<MapLegend metric="closure_rate" scale={{ kind: "numeric", classes: CLASSES }} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(3); // 구간 2 + 데이터 없음 1
  expect(screen.getByText("2.0% ~ 5.0%")).toBeInTheDocument();
  expect(screen.getByText("데이터 없음")).toBeInTheDocument();
});

it("classes가 비어 있으면 아무것도 렌더링하지 않는다", () => {
  const { container } = render(<MapLegend metric="closure_rate" scale={{ kind: "numeric", classes: [] }} />);
  expect(container).toBeEmptyDOMElement();
});

it("'업종 무관' 단서는 더 이상 범례에 없다 — 컨트롤바의 동네/업종 무리가 그 뜻을 말한다", () => {
  render(<MapLegend metric="operating_months" scale={{ kind: "numeric", classes: CLASSES }} />);
  expect(screen.queryByText(/업종 구분 없는/)).toBeNull();
});

it("심야 체류에는 값의 기준(1.00 = 하루 평균)을 붙인다", () => {
  render(<MapLegend metric="night_index" scale={{ kind: "numeric", classes: [{ color: "#abc", from: 0.9, to: 1.1 }] }} />);
  expect(screen.getByText("1.00 = 하루 평균")).toBeInTheDocument();
  expect(screen.getByText("0.90 ~ 1.10")).toBeInTheDocument();
});

it("범주 범례는 값 구간 대신 유형 이름 6줄 + 괄호 설명을 띄운다", () => {
  const classes = ["office", "campus", "dining", "hub", "residential", "mixed"].map((code) => ({ code, color: "#123456" }));
  render(<MapLegend metric="neighborhood_type" scale={{ kind: "categorical", classes }} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(7); // 유형 6 + 데이터 없음 1
  expect(screen.getByText("낮 인구 우위형")).toBeInTheDocument();
  expect(screen.getByText("(주택가)")).toBeInTheDocument();
  expect(screen.getByText("동네 유형")).toBeInTheDocument();
  expect(screen.queryByText(/~/)).toBeNull();
});
