import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/client";
import { fetchCommerceChangeDetail, fetchHourGaps, fetchRegionProfile, fetchRegionSummary } from "../api";
import { SidePanel } from "./side-panel";

vi.mock("../api", () => ({
  fetchRegionSummary: vi.fn(),
  fetchRegionProfile: vi.fn(),
  fetchHourGaps: vi.fn(),
  fetchCommerceChangeDetail: vi.fn(),
}));
vi.mock("next/link", () => ({ default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a> }));

const REGION = "1168064000";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchRegionSummary).mockResolvedValue({ region_code: REGION, name: "역삼1동", industry_id: "cafe", cards: [{ label: "점포수", value: "312", grade: "fact" }] });
  vi.mocked(fetchRegionProfile).mockImplementation(async (_, quarter) => ({
    region_code: REGION, year_quarter: quarter ?? "20262", neighborhood_type: "office", type_reason: "직장인구 중심",
    time_label: "day", peak_block: "day", trough_block: "night", worker_resident_ratio: 5.9, weekend_index: 0.7,
    night_index: 0.64, footfall_20s_share: 0.22, fnb_share: 0.016, facility_total: 542, resident_total: 34082,
    block_intensities: { morning: 0.974, day: 1.4, evening: 1.138, night: 0.687 },
  }));
  vi.mocked(fetchHourGaps).mockImplementation(async (_, __, quarter) => ({
    region_code: REGION, industry_id: "cafe", year_quarter: quarter ?? "20254", bands: [
      { hour_band: "11_14", footfall_intensity: 1.39, sales_intensity: 2.99, gap: 1.6 },
    ],
  }));
  vi.mocked(fetchCommerceChangeDetail).mockImplementation(async (_, quarter) => ({
    region_code: REGION, year_quarter: quarter ?? "20262", change_code: "LL", change_name: "다이나믹",
    operating_months: 110, closed_months: 48, seoul: { operating_months: 118, closed_months: 54 },
  }));
});

function renderPanel(yearQuarter: string | null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = (quarter: string | null) => (
    <QueryClientProvider client={client}>
      <SidePanel regionCode={REGION} industry="cafe" yearQuarter={quarter} />
    </QueryClientProvider>
  );
  const rendered = render(view(yearQuarter));
  return { ...rendered, rerenderQuarter: (quarter: string | null) => rendered.rerender(view(quarter)) };
}

describe("선택 분기의 사이드패널", () => {
  it("20211을 모든 분기 조회에 전달하고 응답 분기를 각 섹션에 표시한다", async () => {
    const { rerenderQuarter } = renderPanel("20211");
    await waitFor(() => expect(fetchHourGaps).toHaveBeenCalledWith(REGION, "cafe", "20211"));
    expect(fetchRegionProfile).toHaveBeenCalledWith(REGION, "20211");
    expect(fetchCommerceChangeDetail).toHaveBeenCalledWith(REGION, "20211");
    expect(await within(screen.getByRole("region", { name: "하루 흐름" })).findByText(/2021년 1분기/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText(/2021년 1분기/)).toHaveLength(4));
    expect(screen.queryByText(/2026년 2분기/)).toBeNull();

    rerenderQuarter("20262");
    await waitFor(() => expect(fetchRegionProfile).toHaveBeenCalledWith(REGION, "20262"));
    expect(fetchHourGaps).toHaveBeenCalledWith(REGION, "cafe", "20262");
    expect(fetchCommerceChangeDetail).toHaveBeenCalledWith(REGION, "20262");

    rerenderQuarter(null);
    await waitFor(() => expect(fetchRegionProfile).toHaveBeenCalledWith(REGION, undefined));
    expect(fetchHourGaps).toHaveBeenCalledWith(REGION, "cafe", undefined);
    expect(fetchCommerceChangeDetail).toHaveBeenCalledWith(REGION, undefined);
  });

  it("선택 분기의 404는 자료 없음이고 다른 실패는 오류로 알린다", async () => {
    vi.mocked(fetchRegionProfile).mockRejectedValue(new ApiError("REGION_PROFILE_NOT_FOUND", "missing"));
    vi.mocked(fetchHourGaps).mockRejectedValue(new ApiError("HOUR_GAP_NOT_FOUND", "missing"));
    vi.mocked(fetchCommerceChangeDetail).mockRejectedValue(new ApiError("COMMERCE_CHANGE_NOT_FOUND", "missing"));
    renderPanel("20211");
    await waitFor(() => expect(screen.getAllByText("해당 분기 자료 없음")).toHaveLength(4));
    expect(screen.queryByText(/2026년 2분기/)).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("통신 실패는 자료 없음으로 바꾸지 않고 오류로 알린다", async () => {
    vi.mocked(fetchRegionProfile).mockRejectedValue(new Error("offline"));
    vi.mocked(fetchHourGaps).mockRejectedValue(new Error("offline"));
    vi.mocked(fetchCommerceChangeDetail).mockRejectedValue(new Error("offline"));
    renderPanel("20211");
    await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(4));
    expect(screen.queryByText("해당 분기 자료 없음")).toBeNull();
  });

  it("요약 조회가 실패해도 분기별 섹션을 독립적으로 표시한다", async () => {
    vi.mocked(fetchRegionSummary).mockRejectedValue(new Error("offline"));
    renderPanel("20211");
    expect((await screen.findAllByText(/2021년 1분기/)).length).toBeGreaterThan(0);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
