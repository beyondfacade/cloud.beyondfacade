import { render, screen } from "@testing-library/react";
import { ChildcareSummaryList } from "./childcare-summary";

it("운영 시설 수·가동률(현원/정원)·입소대기를 행으로 렌더링한다", () => {
  render(
    <ChildcareSummaryList
      summary={{
        region_code: "1111051500",
        base_date: "2026-09-17",
        center_count: 4,
        capacity: 332,
        child_count: 206,
        occupancy_rate: 0.6205,
        waiting_count: 108,
      }}
    />,
  );
  expect(screen.getByText("4곳")).toBeInTheDocument();
  expect(screen.getByText("62.1%")).toBeInTheDocument();
  expect(screen.getByText("현원 206 / 정원 332")).toBeInTheDocument();
  expect(screen.getByText("108건")).toBeInTheDocument();
  expect(screen.getByText("기준일 2026-09-17")).toBeInTheDocument();
});

it("운영 시설이 없으면 안내 문구만 보여준다", () => {
  render(
    <ChildcareSummaryList
      summary={{
        region_code: "1111051500",
        base_date: null,
        center_count: 0,
        capacity: 0,
        child_count: 0,
        occupancy_rate: null,
        waiting_count: null,
      }}
    />,
  );
  expect(screen.getByText("운영 중인 어린이집이 없습니다.")).toBeInTheDocument();
  expect(screen.queryByText("가동률")).not.toBeInTheDocument();
});
