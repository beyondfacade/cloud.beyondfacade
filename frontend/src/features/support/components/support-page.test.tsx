import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { SupportGuide, SupportItem } from "@/shared/api/types";
import { SupportPage } from "./support-page";

let searchParams = new URLSearchParams();
const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
  useRouter: () => ({ push: navigation.push }),
}));

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
  search: null,
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
  navigation.push.mockReset();
  navigation.push.mockImplementation((href: string) => {
    searchParams = new URLSearchParams(href.split("?")[1]);
  });
  stubFetch(GUIDE);
});
afterEach(() => vi.unstubAllGlobals());

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<SupportPage />, {
    wrapper: ({ children }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>,
  });
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
  expect(within(loans).getByText(/출처: 기업마당/)).toBeInTheDocument();
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

it("리포트로 돌아가는 링크와 자금 계획 링크가 동·업종·예산을 유지한다", async () => {
  renderPage();
  await screen.findByRole("region", { name: "대출·보증" });
  expect(screen.getByRole("link", { name: "← 리포트로" })).toHaveAttribute("href", "/analysis?region=1168064000&industry=korean_food&budget=50000000");
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

it("질문을 Enter로 제출하면 URL과 조회에 싣고 지우면 검색을 해제한다", async () => {
  const user = userEvent.setup();
  const { rerender } = renderPage();
  await screen.findByRole("region", { name: "대출·보증" });
  const input = screen.getByRole("textbox", { name: /찾는 지원을 적어 보세요/ });
  await user.type(input, "  인테리어 비용  ");
  expect(fetchMock.mock.calls.filter(([url]) => url.includes("/funding/support"))).toHaveLength(1);
  await user.keyboard("{Enter}");
  expect(navigation.push).toHaveBeenCalledWith(
    `/support?region=1168064000&industry=korean_food&budget=50000000&q=${encodeURIComponent("인테리어 비용").replaceAll("%20", "+")}`,
    { scroll: false },
  );
  rerender(<SupportPage />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("q=" + encodeURIComponent("인테리어 비용").replaceAll("%20", "+")), undefined));
  expect(screen.getByRole("textbox")).toHaveValue("인테리어 비용");
  await user.click(screen.getByRole("button", { name: "지우기" }));
  rerender(<SupportPage />);
  expect(searchParams.has("q")).toBe(false);
  expect(screen.getByRole("textbox")).toHaveValue("");
});

it("찾기 버튼으로 제출한 질문의 결과 절에 기존 카드와 출처를 보여 준다", async () => {
  const { rerender } = renderPage();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "인테리어" } });
  fireEvent.click(screen.getByRole("button", { name: "찾기" }));
  stubFetch({ ...GUIDE, search: { query: "인테리어", available: true, items: [item("s1", "인테리어 비용 지원")] } });
  rerender(<SupportPage />);
  const results = await screen.findByRole("region", { name: "질문과 가까운 공고" });
  expect(within(results).getByText("지원 자격(서울·소상공인·창업, 마감 전)으로 먼저 거른 뒤 질문과 가까운 순서예요")).toBeInTheDocument();
  expect(within(results).getByRole("link", { name: "인테리어 비용 지원" })).toHaveAttribute("href", "https://www.bizinfo.go.kr/s1");
  expect(within(results).getByText(/출처: 기업마당/)).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "대출·보증" })).toBeInTheDocument();
});

it("검색을 쓸 수 없으면 안내하고 기존 목록을 보여 준다", async () => {
  searchParams.set("q", "청년 대출");
  stubFetch({ ...GUIDE, search: { query: "청년 대출", available: false, items: [] } });
  renderPage();
  expect(await screen.findByText("지금은 검색을 쓸 수 없어요. 아래 목록을 확인해 주세요.")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "대출·보증" })).toBeInTheDocument();
});

it("검색 결과는 처음 8건을 보여 주고 8건씩 더 펼치며 새 질문이면 초기화한다", async () => {
  searchParams.set("q", "지원");
  const items = Array.from({ length: 17 }, (_, index) => item(`s${index}`, `검색 공고 ${index + 1}`));
  stubFetch({ ...GUIDE, search: { query: "지원", available: true, items } });
  const { rerender } = renderPage();
  const results = await screen.findByRole("region", { name: "질문과 가까운 공고" });
  expect(within(results).getByText("관련 공고 17건")).toBeInTheDocument();
  expect(within(results).getAllByRole("listitem")).toHaveLength(8);
  expect(within(results).queryByRole("link", { name: "검색 공고 9" })).toBeNull();

  fireEvent.click(within(results).getByRole("button", { name: "더보기 (9건 더)" }));
  expect(within(results).getAllByRole("listitem")).toHaveLength(16);
  expect(within(results).getByRole("link", { name: "검색 공고 9" })).toBeInTheDocument();
  fireEvent.click(within(results).getByRole("button", { name: "더보기 (1건 더)" }));
  expect(within(results).getAllByRole("listitem")).toHaveLength(17);
  expect(within(results).queryByRole("button", { name: /더보기/ })).toBeNull();

  searchParams.set("q", "창업");
  stubFetch({ ...GUIDE, search: { query: "창업", available: true, items } });
  rerender(<SupportPage />);
  await waitFor(() => expect(within(screen.getByRole("region", { name: "질문과 가까운 공고" })).getAllByRole("listitem")).toHaveLength(8));
  expect(screen.getByRole("button", { name: "더보기 (9건 더)" })).toBeInTheDocument();
});

it("검색 결과가 8건이면 모두 보여 주고 더보기 버튼을 숨긴다", async () => {
  searchParams.set("q", "지원");
  const items = Array.from({ length: 8 }, (_, index) => item(`s${index}`, `검색 공고 ${index + 1}`));
  stubFetch({ ...GUIDE, search: { query: "지원", available: true, items } });
  renderPage();
  const results = await screen.findByRole("region", { name: "질문과 가까운 공고" });
  expect(within(results).getByText("관련 공고 8건")).toBeInTheDocument();
  expect(within(results).getAllByRole("listitem")).toHaveLength(8);
  expect(within(results).queryByRole("button", { name: /더보기/ })).toBeNull();
});

it("검색 결과가 비면 다른 말로 찾도록 안내한다", async () => {
  searchParams.set("q", "인테리어");
  stubFetch({ ...GUIDE, search: { query: "인테리어", available: true, items: [] } });
  renderPage();
  expect(await screen.findByText("맞는 공고를 찾지 못했어요. 다른 말로 찾아보세요.")).toBeInTheDocument();
});
