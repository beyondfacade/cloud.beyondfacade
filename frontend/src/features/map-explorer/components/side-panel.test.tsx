import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/client";
import * as api from "../api";
import { SidePanel } from "./side-panel";

vi.mock("../api", () => ({
  fetchRegionSummary: vi.fn(async () => ({ region_code: "1168064000", name: "역삼1동", industry_id: "cafe", cards: [{ label: "점포수", value: "312", grade: "fact" }] })),
  fetchStores: vi.fn(async () => []),
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
  fetchVerdict: vi.fn(async () => {
    throw new ApiError("VERDICT_NOT_FOUND", "missing");
  }),
  fetchVerdictAlternatives: vi.fn(async () => {
    throw new ApiError("VERDICT_NOT_FOUND", "missing");
  }),
  fetchConvenienceSummary: vi.fn(async () => ({ region_code: "1168064000", store_count: 0, brands: [], source_stdr_ym: null })),
}));

vi.mock("next/link", () => ({ default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a> }));

function renderPanel(props: Partial<React.ComponentProps<typeof SidePanel>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SidePanel regionCode="1168064000" industry="cafe" {...props} />
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

  it("폐업 점포 토글을 켜면 최근 2년 폐업 건수를 한 줄로 보여준다", async () => {
    vi.spyOn(api, "fetchStores").mockResolvedValue([
      { store_id: "c1", name: "a", lat: 37.5, lng: 127, status_name: "폐업", open_date: "2023-01-01", close_date: "2025-01-01" },
      { store_id: "c2", name: "b", lat: 37.5, lng: 127, status_name: "폐업", open_date: "2023-02-01", close_date: "2025-02-01" },
    ]);
    const onToggle = vi.fn();
    renderPanel({ regionCode: "1168064000", industry: "korean_food", showClosed: true, onToggleClosed: onToggle });
    // 건수는 <span className="tabular-nums"> 안에 있어 텍스트가 여러 노드로 쪼개진다 — RTL 기본 매처는 이를 못 찾으므로 textContent 함수 매처를 쓴다.
    expect(
      await screen.findByText((_, node) => node?.textContent === "이 동에서 최근 2년 한식 2곳 폐업"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /최근 2년 폐업 점포 보기/ }));
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it("스냅샷 원천 업종(편의점)은 폐업 이력이 없어 토글이 아예 뜨지 않는다", async () => {
    renderPanel({ regionCode: "1168064000", industry: "convenience_store" });
    await screen.findByText("낮 인구 우위형");
    expect(screen.queryByRole("checkbox", { name: /최근 2년 폐업 점포 보기/ })).toBeNull();
  });
});
