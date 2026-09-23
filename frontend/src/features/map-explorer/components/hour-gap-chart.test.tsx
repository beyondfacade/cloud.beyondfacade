import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { HourGapBand } from "@/shared/api/types";
import { HourGapBody, HourGapLines } from "./hour-gap-chart";

function band(hour_band: string, footfall: number, sales: number): HourGapBand {
  return { hour_band, footfall_intensity: footfall, sales_intensity: sales, gap: sales - footfall };
}
// 역삼1동×카페 20254 모양
const BANDS = [band("00_06", 0.3, 0.05), band("06_11", 1.0, 0.7), band("11_14", 1.39, 2.99),
  band("14_17", 1.4, 1.6), band("17_21", 1.1, 1.2), band("21_24", 0.5, 0.35)];

describe("시간대 두 선", () => {
  it("유동·매출 두 선을 그리고 gap 막대는 그리지 않는다", () => {
    const { container } = render(<HourGapLines bands={BANDS} />);
    expect(container.querySelector('polyline[data-series="footfall"]')).not.toBeNull();
    expect(container.querySelector('polyline[data-series="sales"]')).not.toBeNull();
    expect(container.querySelectorAll("polyline")).toHaveLength(2);
    expect(container.querySelectorAll("rect")).toHaveLength(0);
  });

  it("각 선이 6개 점을 갖는다", () => {
    const { container } = render(<HourGapLines bands={BANDS} />);
    const pts = container.querySelector('polyline[data-series="sales"]')!.getAttribute("points")!;
    expect(pts.trim().split(/\s+/)).toHaveLength(6);
  });

  it("x축에 구간 6개를 짧은 한국어로 붙인다", () => {
    render(<HourGapLines bands={BANDS} />);
    for (const label of ["새벽", "아침", "점심", "오후", "저녁", "밤"]) expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("두 최대 구간을 말하는 문장과 기준 분기를 곁들인다", () => {
    render(<HourGapBody gap={{ region_code: "1168064000", industry_id: "cafe", year_quarter: "20254", bands: BANDS }} />);
    expect(screen.getByText("사람은 오후(14~17시)에 가장 많고, 돈은 점심(11~14시)에 돕니다.")).toBeInTheDocument();
    expect(screen.getByText(/2025년 4분기/)).toBeInTheDocument();
  });
});
