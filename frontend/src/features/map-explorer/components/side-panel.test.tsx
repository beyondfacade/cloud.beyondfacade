import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SidePanel } from "./side-panel";

vi.mock("../api", () => ({
  fetchRegionSummary: vi.fn(async () => ({ region_code: "1168064000", name: "역삼1동", industry_id: "cafe", cards: [{ label: "점포수", value: "312", grade: "fact" }] })),
  fetchRegionProfile: vi.fn(async () => ({
    region_code: "1168064000", year_quarter: "20262", neighborhood_type: "office", type_reason: "직장인구가 상주인구의 5.9배",
    time_label: "day", peak_block: "day", trough_block: "night", worker_resident_ratio: 5.9, weekend_index: 0.7,
    night_index: 0.64, footfall_20s_share: 0.22, fnb_share: 0.016, facility_total: 542, resident_total: 34082,
    block_intensities: { morning: 0.974, day: 1.4, evening: 1.138, night: 0.687 },
  })),
  fetchHourGaps: vi.fn(async () => ({ region_code: "1168064000", industry_id: "cafe", year_quarter: "20254", bands: [
    { hour_band: "11_14", footfall_intensity: 1.39, sales_intensity: 2.99, gap: 1.6 },
    { hour_band: "14_17", footfall_intensity: 1.4, sales_intensity: 1.6, gap: 0.2 },
  ] })),
  fetchCommerceChangeDetail: vi.fn(async () => ({ region_code: "1168064000", year_quarter: "20262", change_code: "LL", change_name: "다이나믹", operating_months: 110, closed_months: 48, seoul: { operating_months: 118, closed_months: 54 } })),
}));

vi.mock("next/link", () => ({ default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a> }));

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SidePanel regionCode="1168064000" industry="cafe" />
    </QueryClientProvider>,
  );
}

describe("사이드패널 서사 순서", () => {
  it("창업자의 질문 순서로 다섯 섹션이 놓인다", async () => {
    const { container } = renderPanel();
    await screen.findByText("낮 인구 우위형");
    await screen.findByText("110개월");
    await screen.findByText(/돈은 점심/);
    const labels = Array.from(container.querySelectorAll("section[aria-label]")).map((s) => s.getAttribute("aria-label"));
    expect(labels).toEqual(["동네 유형", "하루 흐름", "업종 시간대", "얼마나 버티나", "업종 실적"]);
  });

  it("AI 분석 CTA는 맨 끝에 있고 동·업종을 싣는다", async () => {
    renderPanel();
    const cta = await screen.findByRole("link", { name: "AI 분석 →" });
    expect(cta.getAttribute("href")).toBe("/analysis?region=1168064000&industry=cafe");
  });
});
