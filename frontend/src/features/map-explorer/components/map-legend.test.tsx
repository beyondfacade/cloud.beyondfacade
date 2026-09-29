import { render, screen } from "@testing-library/react";
import { MapLegend } from "./map-legend";

it("판정 네 단계와 데이터 없음만 순서대로 표시한다", () => {
  const classes = ["red", "orange", "clear", "insufficient"].map((code) => ({ code, color: "#123456" }));
  render(<MapLegend scale={{ classes }} />);
  expect(screen.getByText("창업 경고")).toBeInTheDocument();
  const rows = screen.getAllByRole("listitem");
  expect(rows).toHaveLength(5);
  for (const [i, name] of ["비추천", "조건부", "경고 없음", "판정 보류", "데이터 없음"].entries()) {
    expect(rows[i]).toHaveTextContent(name);
  }
  expect(screen.queryByText(/~/)).toBeNull();
});

it("판정 데이터가 없으면 범례를 표시하지 않는다", () => {
  const { container } = render(<MapLegend scale={{ classes: [] }} />);
  expect(container).toBeEmptyDOMElement();
});
