import { render, screen } from "@testing-library/react";
import { expect, it, describe } from "vitest";
import type { RegionProfile } from "@/shared/api/types";
import { NeighborhoodProfileBody } from "./neighborhood-profile";

function profile(overrides: Partial<RegionProfile> = {}): RegionProfile {
  return {
    region_code: "1168064000",
    year_quarter: "20262",
    neighborhood_type: "office",
    type_reason: "직장인구가 상주인구의 5.9배로 서울 상위 10%이고, 주말 유동이 평일보다 적습니다.",
    time_label: "day",
    peak_block: "day",
    trough_block: "night",
    worker_resident_ratio: 5.927,
    weekend_index: 0.698,
    night_index: 0.639,
    footfall_20s_share: 0.2251,
    fnb_share: 0.0163,
    facility_total: 195,
    resident_total: 34082,
    ...overrides,
  };
}

describe("동네 프로필 섹션", () => {
  it("유형 이름과 괄호 설명을 함께 띄운다", () => {
    render(<NeighborhoodProfileBody profile={profile()} />);

    expect(screen.getByText("낮 인구 우위형")).toBeTruthy();
    expect(screen.getByText(/낮에 사람이 몰리는 곳/)).toBeTruthy();
  });

  it("판정 근거 문장을 그대로 보여준다", () => {
    render(<NeighborhoodProfileBody profile={profile()} />);

    expect(screen.getByText(/5\.9배로 서울 상위 10%/)).toBeTruthy();
  });

  it("정점→바닥 쌍이 있으면 그 서사를 쓴다", () => {
    render(<NeighborhoodProfileBody profile={profile()} />);

    expect(screen.getByText(/밤이면 텅 빕니다/)).toBeTruthy();
  });

  it("서사가 없는 쌍이면 시간대 라벨 문장으로 대체한다", () => {
    // 전 서울에 7개 동뿐인 하위 조합 — 억지 문장을 만들지 않는다
    render(
      <NeighborhoodProfileBody
        profile={profile({ peak_block: "morning", trough_block: "evening", time_label: "morning" })}
      />,
    );

    expect(screen.getByText(/출근길에만 붐비는 동네/)).toBeTruthy();
  });

  it("직장인구가 결측인 동은 0이 아니라 집계 없음으로 표시한다", () => {
    render(<NeighborhoodProfileBody profile={profile({ worker_resident_ratio: null })} />);

    expect(screen.getByText("집계 없음")).toBeTruthy();
    expect(screen.queryByText("0.0배")).toBeNull();
  });

  it("기준 분기를 밝힌다", () => {
    render(<NeighborhoodProfileBody profile={profile()} />);

    expect(screen.getByText(/2026년 2분기/)).toBeTruthy();
  });

  it("알 수 없는 유형이 와도 화면이 비지 않는다", () => {
    render(<NeighborhoodProfileBody profile={profile({ neighborhood_type: "brand_new" })} />);

    expect(screen.getByText("brand_new")).toBeTruthy();
  });
});
