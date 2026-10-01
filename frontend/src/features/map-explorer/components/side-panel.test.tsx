import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { verdictExclusionNotice } from "@/shared/verdict";
import { SidePanel } from "./side-panel";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: string) => {
    const url = new URL(input, "http://localhost");
    const path = url.pathname;
    if (path.includes("/regions/")) return Response.json({ region_code: "1168064000", name: "역삼1동", industry_id: url.searchParams.get("industry"), cards: [{ label: "점포수", value: "312", grade: "fact" }] });
    if (path.includes("/profiles/")) return Response.json({
      region_code: "1168064000", year_quarter: "20262", neighborhood_type: "office", type_reason: "직장인구가 상주인구의 5.9배",
      time_label: "day", peak_block: "day", trough_block: "night", worker_resident_ratio: 5.9, weekend_index: 0.7,
      night_index: 0.64, footfall_20s_share: 0.22, fnb_share: 0.016, facility_total: 542, resident_total: 34082,
      block_intensities: { morning: 0.974, day: 1.4, evening: 1.138, night: 0.687 },
    });
    if (path.endsWith("/alternatives")) return Response.json({
      region_code: "1168064000", industry_id: "cafe", neighborhood_type: "office",
      industries: [{ industry_id: "snack", industry_name: "분식", verdict_code: "clear", strong_count: 0, on_count: 0 }],
      regions: [{ region_code: "1168065000", region_name: "역삼2동", verdict_code: "orange", strong_count: 0, on_count: 1 }],
    });
    if (path.includes("/verdicts/")) return Response.json({
      basis: "permit",
      region_code: "1168064000", industry_id: url.searchParams.get("industry"), verdict_code: "orange", on_count: 1, strong_count: 0,
      signals: [{ key: "net_outflow", level: "on", evidence: "순유출 근거", source: "store", value: 0.1, percentile: 80 }], computed_at: "2026-09-29T04:30:00+09:00",
    });
    if (path.endsWith("/stores")) return Response.json([
      { store_id: "c1", name: "a", lat: 37.5, lng: 127, status_name: "폐업", open_date: "2023-01-01", close_date: "2025-01-01" },
      { store_id: "c2", name: "b", lat: 37.5, lng: 127, status_name: "폐업", open_date: "2023-02-01", close_date: "2025-02-01" },
    ]);
    if (path.endsWith("/convenience-stores/summary")) return Response.json({ region_code: "1168064000", store_count: 149, brands: [{ brand: "GS25", count: 54 }], source_stdr_ym: "202606" });
    return Response.json({ error: { code: "NOT_FOUND", message: "자료 없음" } }, { status: 404 });
  }));
});
afterEach(() => vi.unstubAllGlobals());

function renderPanel(props: Partial<React.ComponentProps<typeof SidePanel>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SidePanel regionCode="1168064000" industry="cafe" {...props} />
    </QueryClientProvider>,
  );
}

describe("사이드패널 한 화면 요약", () => {
  it("헤더 다음 판정과 대안, 동네 한 줄, 폐업 토글, 리포트와 자금 계획 순서로 표시한다", async () => {
    renderPanel();
    const ordered = [
      await screen.findByRole("heading", { name: "역삼1동" }),
      await screen.findByRole("region", { name: "창업 경고 판정" }),
      await screen.findByTestId("alt-industries"),
      await screen.findByTestId("alt-regions"),
      await screen.findByText("낮 인구 우위형 · 점심·오후가 하루의 정점"),
      screen.getByRole("checkbox", { name: "최근 2년 폐업 점포 보기" }),
      screen.getByRole("link", { name: "창업 경고 리포트 보기" }),
      screen.getByRole("link", { name: "자금 계획 →" }),
    ];
    ordered.slice(1).forEach((node, i) => {
      expect(ordered[i].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
    expect(screen.getByText(/1168064000/).closest("p")).toHaveTextContent("1168064000 · 카페");
  });

  it.each([null, 0, 50000000])("두 CTA에 동·업종과 예산 %s원을 그대로 전달한다", async (budget) => {
    renderPanel({ budget });
    const suffix = budget === null ? "" : `&budget=${budget}`;
    expect(await screen.findByRole("link", { name: "창업 경고 리포트 보기" })).toHaveAttribute("href", `/analysis?region=1168064000&industry=cafe${suffix}`);
    expect(screen.getByRole("link", { name: "자금 계획 →" })).toHaveAttribute("href", `/plan?region=1168064000&industry=cafe${suffix}`);
  });

  it("상세 섹션과 연간 업종 실적을 brief에 표시하지 않는다", async () => {
    renderPanel();
    await screen.findByRole("heading", { name: "역삼1동" });
    for (const name of ["동네 유형", "하루 흐름", "업종 시간대", "얼마나 버티나", "업종 실적"]) {
      expect(screen.queryByRole("region", { name })).toBeNull();
    }
    expect(screen.queryByText("312")).toBeNull();
    expect(screen.queryByText(/선택 분기와 무관/)).toBeNull();
  });

  it("폐업 점포 토글을 켜면 최근 2년 폐업 건수를 한 줄로 보여준다", async () => {
    const onToggle = vi.fn();
    renderPanel({ industry: "korean_food", showClosed: true, onToggleClosed: onToggle });
    expect(await screen.findByText((_, node) => node?.textContent === "이 동에서 최근 2년 한식 2곳 폐업")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /최근 2년 폐업 점포 보기/ }));
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it("편의점은 판정 준비 중 안내와 현황 한 줄을 보여준다", async () => {
    renderPanel({ industry: "convenience_store" });
    expect(await screen.findByText("편의점 149곳 · 기준 2026년 6월")).toBeInTheDocument();
    expect(screen.getByText(verdictExclusionNotice("convenience_store"))).toBeInTheDocument();
    expect(screen.queryByText("판정은 담배권 특화 신호 단계에서 제공")).toBeNull();
    expect(screen.queryByRole("region", { name: "창업 경고 판정" })).toBeNull();
    expect(screen.queryByText(/낮 인구 우위형/)).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("list", { name: "브랜드별 점포 수" })).toBeNull();
    expect(screen.getByRole("link", { name: "창업 경고 리포트 보기" })).toBeInTheDocument();
  });

  it("부동산은 판정 없이 동네 한 줄과 CTA를 표시한다", async () => {
    renderPanel({ industry: "real_estate" });
    await screen.findByText("낮 인구 우위형 · 점심·오후가 하루의 정점");
    expect(screen.getByText(verdictExclusionNotice("real_estate"))).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "창업 경고 판정" })).toBeNull();
    expect(screen.getByRole("link", { name: "창업 경고 리포트 보기" })).toHaveAttribute("href", "/analysis?region=1168064000&industry=real_estate");
  });

  it("헤더 요약 조회가 실패해도 판정과 동네 한 줄 및 두 CTA를 표시한다", async () => {
    const fetch = globalThis.fetch;
    vi.stubGlobal("fetch", vi.fn((input: string) => input.includes("/regions/")
      ? Promise.resolve(Response.json({ error: { code: "HTTP_500", message: "조회 실패" } }, { status: 500 }))
      : fetch(input)));
    renderPanel({ budget: 50000000 });
    expect(await screen.findByRole("alert")).toHaveTextContent("불러오기 실패");
    expect(await screen.findByRole("region", { name: "창업 경고 판정" })).toBeInTheDocument();
    expect(await screen.findByText("낮 인구 우위형 · 점심·오후가 하루의 정점")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "창업 경고 리포트 보기" })).toHaveAttribute("href", "/analysis?region=1168064000&industry=cafe&budget=50000000");
    expect(screen.getByRole("link", { name: "자금 계획 →" })).toBeInTheDocument();
  });

  it("동을 선택하지 않으면 선택 안내만 표시한다", () => {
    renderPanel({ regionCode: null });
    expect(screen.getByRole("heading", { name: "어느 동네를 보고 계세요?" })).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("빈 화면은 동을 누르라고 안내하고 배지는 선택된 동 없음이다", () => {
    renderPanel({ regionCode: null });
    expect(screen.getByText("선택된 동 없음")).toBeInTheDocument();
    expect(screen.getByText(/지도에서 동을 누르면 .* 창업 경고 판정과 근거가 여기에 나옵니다\./)).toBeInTheDocument();
  });

  it("불러오는 동안 판정을 불러온다고 알린다", () => {
    renderPanel();
    expect(screen.getByText("판정을 불러오고 있어요.")).toBeInTheDocument();
  });

  it("조회에 실패하면 창업 경고 판정을 불러오지 못했다고 알린다", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: { code: "NOT_FOUND", message: "자료 없음" } }, { status: 404 })));
    renderPanel();
    expect(await screen.findByText(/행정동의 .* 창업 경고 판정을 불러오지 못했습니다\./)).toBeInTheDocument();
  });
});
