import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RegionProfile } from "@/shared/api/types";
import { TimeBlockBars, TimeBlockBody } from "./time-block-bars";

const BLOCKS = { morning: 0.974, day: 1.4, evening: 1.138, night: 0.687 }; // 역삼1동 20262 실측

function profile(overrides: Partial<RegionProfile> = {}): RegionProfile {
  return {
    region_code: "1168064000", year_quarter: "20262", neighborhood_type: "office",
    type_reason: "…", time_label: "day", peak_block: "day", trough_block: "night",
    worker_resident_ratio: 5.9, weekend_index: 0.7, night_index: 0.64, footfall_20s_share: 0.22,
    fnb_share: 0.016, facility_total: 542, resident_total: 34082, block_intensities: BLOCKS, ...overrides,
  };
}

describe("4블록 막대", () => {
  it("막대 4개를 그리고 정점 블록만 강조한다", () => {
    const { container } = render(<TimeBlockBars blocks={BLOCKS} peak="day" />);
    const rects = container.querySelectorAll("rect");
    expect(rects).toHaveLength(4);
    const peaks = Array.from(rects).filter((r) => r.getAttribute("data-peak") === "true");
    expect(peaks).toHaveLength(1);
    expect(peaks[0].getAttribute("data-block")).toBe("day");
  });

  it("가장 큰 블록의 막대가 가장 높다 — 배치 값을 다시 계산하지 않고 그대로 그린다", () => {
    const { container } = render(<TimeBlockBars blocks={BLOCKS} peak="day" />);
    const height = (block: string) =>
      Number(container.querySelector(`rect[data-block="${block}"]`)!.getAttribute("height"));
    expect(height("day")).toBeGreaterThan(height("evening"));
    expect(height("evening")).toBeGreaterThan(height("morning"));
    expect(height("morning")).toBeGreaterThan(height("night"));
  });

  it("블록 이름 4개를 한국어로 붙인다", () => {
    render(<TimeBlockBars blocks={BLOCKS} peak={null} />);
    for (const label of ["아침", "낮", "저녁", "밤"]) expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("정점→바닥 서사를 곁들인다", () => {
    render(<TimeBlockBody profile={profile()} />);
    expect(screen.getByText(/밤이면 텅 빕니다/)).toBeInTheDocument();
  });

  it("블록 값이 없으면 막대 대신 안내 한 줄", () => {
    const { container } = render(<TimeBlockBody profile={profile({ block_intensities: null })} />);
    expect(container.querySelector("svg")).toBeNull();
    expect(screen.getByText("시간대 자료가 없습니다.")).toBeInTheDocument();
  });
});
