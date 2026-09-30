import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { SupportGuide, SupportItem } from "@/shared/api/types";
import { SupportPage } from "./support-page";

let searchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({ useSearchParams: () => searchParams }));

function item(id: string, title: string, extra: Partial<SupportItem> = {}): SupportItem {
  return {
    program_id: id, source: "bizinfo", title, org: "서울특별시", url: `https://www.bizinfo.go.kr/${id}`,
    apply_period: "2026-09-10 ~ 2026-10-07", exec_org: null, field_category: "경영", field_subcategory: null,
    target_text: "소상공인", hashtags: null, apply_begin: null, deadline: "2026-10-07", summary: null,
    is_expired: false, why: "서울 · 소상공인 · 경영", district_match: false, industry_match: false, ...extra,
  };
}

const GUIDE: SupportGuide = {
  region_code: "1168064000",
  district_name: "강남구",
  industry_id: "korean_food",
  loans: [item("l1", "소상공인 정책자금 융자", { field_category: "금융", why: "전국 · 소상공인 · 금융" })],
  district: [item("d1", "강남구 소상공인 경영 지원", { district_match: true })],
  others: [item("o1", "외식업 소상공인 배달비 지원", { industry_match: true })],
  rates: [
    { rate_type: "base", period: "202608", rate_pct: 3 },
    { rate_type: "loan_facility", period: "202608", rate_pct: 4.05 },
  ],
};

let fetchMock: ReturnType<typeof vi.fn>;
function stubFetch(guide: SupportGuide | null) {
  fetchMock = vi.fn(async (url: string) => {
    if (url.includes("/funding/support")) return guide ? Response.json(guide) : new Response("{}", { status: 500 });
    return Response.json({ region_code: "1168064000", name: "역삼1동", industry_id: "korean_food", cards: [] });
  });
  vi.stubGlobal("fetch", fetchMock);
}

beforeEach(() => {
  searchParams = new URLSearchParams("region=1168064000&industry=korean_food&budget=50000000");
  stubFetch(GUIDE);
});
afterEach(() => vi.unstubAllGlobals());

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><SupportPage /></QueryClientProvider>);
}

it("동·업종으로 지원 정보를 불러와 동네 이름과 업종을 제목 옆에 보여 준다", async () => {
  renderPage();
  expect(await screen.findByText("역삼1동")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "창업 지원·대출 정보" })).toBeInTheDocument();
  expect(screen.getByText("한식")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/funding/support?region=1168064000&industry=korean_food"), undefined);
});

it("대출·보증 묶음에 금리 참고값과 대출 공고를 보여 준다", async () => {
  renderPage();
  const loans = await screen.findByRole("region", { name: "대출·보증" });
  expect(within(loans).getByText("한국은행 기준금리")).toBeInTheDocument();
  expect(within(loans).getByText("연 3.00%")).toBeInTheDocument();
  expect(within(loans).getByText("은행 시설자금대출 평균 금리")).toBeInTheDocument();
  expect(within(loans).getByText("연 4.05%")).toBeInTheDocument();
  expect(within(loans).getAllByText(/2026년 8월/).length).toBeGreaterThan(0);
  expect(within(loans).getByRole("link", { name: "소상공인 정책자금 융자" })).toHaveAttribute("href", "https://www.bizinfo.go.kr/l1");
});

it("우리 구 전용 묶음 제목에 구 이름을 쓰고 전용 표시를 단다", async () => {
  renderPage();
  const district = await screen.findByRole("region", { name: "강남구 전용 지원" });
  expect(within(district).getByRole("link", { name: "강남구 소상공인 경영 지원" })).toBeInTheDocument();
  expect(within(district).getByText("강남구 전용")).toBeInTheDocument();
});

it("창업·경영 묶음의 업종 관련 공고에 업종 관련 표시를 단다", async () => {
  renderPage();
  const others = await screen.findByRole("region", { name: "창업·경영 지원" });
  expect(within(others).getByText("업종 관련")).toBeInTheDocument();
});

it("공식 상담·신청 창구 링크를 새 창으로 연다", async () => {
  renderPage();
  const channels = await screen.findByRole("region", { name: "상담·신청 창구" });
  const links = within(channels).getAllByRole("link");
  expect(links.length).toBeGreaterThanOrEqual(4);
  for (const link of links) {
    expect(link.getAttribute("href")).toMatch(/^https:\/\//);
    expect(link).toHaveAttribute("target", "_blank");
  }
  expect(within(channels).getByRole("link", { name: /서울신용보증재단/ })).toBeInTheDocument();
});

it("분석 결과로 돌아가는 링크와 자금 계획 링크가 동·업종·예산을 유지한다", async () => {
  renderPage();
  await screen.findByRole("region", { name: "대출·보증" });
  expect(screen.getByRole("link", { name: "← 분석 결과로" })).toHaveAttribute("href", "/analysis?region=1168064000&industry=korean_food&budget=50000000");
  expect(screen.getByRole("link", { name: /필요한 자금 계산하기/ })).toHaveAttribute("href", "/plan?region=1168064000&industry=korean_food&budget=50000000");
});

it("구 전용 공고가 없으면 없다고 말하고, 구를 모르면 구 묶음을 그리지 않는다", async () => {
  stubFetch({ ...GUIDE, district: [] });
  const { unmount } = renderPage();
  const district = await screen.findByRole("region", { name: "강남구 전용 지원" });
  expect(within(district).getByText("지금 강남구 전용으로 모집 중인 공고는 없습니다.")).toBeInTheDocument();
  unmount();

  stubFetch({ ...GUIDE, district_name: null, district: [] });
  renderPage();
  await screen.findByRole("region", { name: "대출·보증" });
  expect(screen.queryByRole("region", { name: /전용 지원/ })).toBeNull();
});

it("지원 정보를 불러오지 못하면 알리고 상담 창구는 그대로 보여 준다", async () => {
  stubFetch(null);
  renderPage();
  expect(await screen.findByRole("alert")).toHaveTextContent("지원 공고를 불러오지 못했습니다.");
  expect(screen.getByRole("region", { name: "상담·신청 창구" })).toBeInTheDocument();
});

it("자격 확정이 아니라는 안내를 상단에 고정한다", async () => {
  renderPage();
  expect(await screen.findByText(/자격 확정이 아니라/)).toBeInTheDocument();
});
