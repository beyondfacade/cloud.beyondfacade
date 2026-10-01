import { render, screen } from "@testing-library/react";
import Home from "./page";

// 관문(IntentGate)이 useRouter를 쓴다 — redirect는 원본 그대로 두고 라우터만 스텁한다
vi.mock("next/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("@/shared/ui/account-menu", () => ({ AccountMenu: () => null }));

it("이전 지도 주소의 선택값을 보존하여 지도 경로로 이동한다", async () => {
  const result = Promise.resolve().then(() => Home({ searchParams: Promise.resolve({
    region: "1168064000", industry: "cafe", year: "2025",
  }) }));
  await expect(result).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/map?region=1168064000&industry=cafe&year=2025;307;",
  });
});

it("반복된 검색값과 특수문자도 지도 주소에 보존한다", async () => {
  const result = Promise.resolve().then(() => Home({ searchParams: Promise.resolve({
    metric: "", region: ["1168064000", "1168065000"], note: "서울 & 카페", absent: undefined,
  }) }));
  await expect(result).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/map?metric=&region=1168064000&region=1168065000&note=%EC%84%9C%EC%9A%B8+%26+%EC%B9%B4%ED%8E%98;307;",
  });
});

it.each([{}, { utm_source: "newsletter" }])("지도 선택값이 없는 방문에는 경고 지도 링크를 제공한다 (%j)", async (query) => {
  render(await Home({ searchParams: Promise.resolve(query) }));
  expect(screen.getByRole("link", { name: "창업 경고 지도 보기" })).toHaveAttribute("href", "/map");
});

it("지도 선택값이 없는 방문에는 관문 입력창이 히어로에 있다", async () => {
  render(await Home({ searchParams: Promise.resolve({}) }));
  expect(screen.getByLabelText("어느 동네에서 무엇을 하려고 하세요?")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "역삼동에 카페, 예산 5천" })).toBeInTheDocument();
});

it("랜딩 제목은 피해야 할 자리부터 확인하라고 읽히고 화면 어디에도 가능성이 없다", async () => {
  const { container } = render(await Home({ searchParams: Promise.resolve({}) }));
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("가게 자리를 찾기 전에,피해야 할 자리부터확인하세요.");
  expect(container.textContent).not.toContain("가능성");
});

it("보조 링크 어떻게 판정하나요?는 소개 절을 가리킨다", async () => {
  render(await Home({ searchParams: Promise.resolve({}) }));
  expect(screen.getByRole("link", { name: /어떻게 판정하나요\?/ })).toHaveAttribute("href", "#about");
});
