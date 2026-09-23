import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RegionCommerceChangeDetail } from "@/shared/api/types";
import { StayingPowerBody } from "./staying-power";

function detail(overrides: Partial<RegionCommerceChangeDetail> = {}): RegionCommerceChangeDetail {
  return {
    region_code: "1168064000", year_quarter: "20262", change_code: "LL", change_name: "다이나믹",
    operating_months: 110, closed_months: 48, seoul: { operating_months: 118, closed_months: 54 }, ...overrides,
  };
}

describe("얼마나 버티나", () => {
  it("영업·폐업 개월을 서울 평균과 나란히 놓는다", () => {
    render(<StayingPowerBody detail={detail()} />);
    expect(screen.getByText("110개월")).toBeInTheDocument();
    expect(screen.getByText("· 서울 118")).toBeInTheDocument();
    expect(screen.getByText("48개월")).toBeInTheDocument();
    expect(screen.getByText("· 서울 54")).toBeInTheDocument();
  });

  it("상권변화 배지는 원천 이름 그대로, 색은 코드로 정한다", () => {
    render(<StayingPowerBody detail={detail()} />);
    const badge = screen.getByText("다이나믹");
    expect(badge.getAttribute("data-change-code")).toBe("LL");
  });

  it("서울 평균이 없으면 서울 절을 뺀다", () => {
    render(<StayingPowerBody detail={detail({ seoul: null })} />);
    expect(screen.queryByText(/서울/)).toBeNull();
  });

  it("결측은 0이 아니라 집계 없음이다", () => {
    render(<StayingPowerBody detail={detail({ closed_months: null, seoul: { operating_months: 118, closed_months: null } })} />);
    expect(screen.getByText("집계 없음")).toBeInTheDocument();
    expect(screen.queryByText("0개월")).toBeNull();
  });
});
