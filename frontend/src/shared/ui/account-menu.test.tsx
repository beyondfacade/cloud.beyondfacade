import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AccountMenu } from "./account-menu";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/map",
  useRouter: () => ({ refresh }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  refresh.mockReset();
});

const json = (status: number, body: unknown) => new Response(status === 204 ? null : JSON.stringify(body), { status });
const UNAUTHENTICATED = { error: { code: "UNAUTHENTICATED", message: "로그인이 필요합니다." } };

function renderMenu(me: unknown) {
  const fetch = vi.fn((url: string) =>
    Promise.resolve(url.endsWith("/admin/auth/logout") ? json(204, null) : me ? json(200, me) : json(401, UNAUTHENTICATED)),
  );
  vi.stubGlobal("fetch", fetch);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><AccountMenu /></QueryClientProvider>);
  return fetch;
}

it("비로그인이면 지금 화면으로 돌아오는 로그인·회원가입 링크를 보여준다", async () => {
  renderMenu(null);
  expect(await screen.findByRole("link", { name: "로그인" })).toHaveAttribute("href", "/login?next=%2Fmap");
  expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute("href", "/signup?next=%2Fmap");
});

it("일반 회원은 이름과 일반 등급, 관리자 페이지 링크를 본다", async () => {
  renderMenu({ username: "kim", role: "viewer", can_operate: false });
  expect(await screen.findByText("kim")).toBeInTheDocument();
  expect(screen.getByText("일반")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "관리자 페이지" })).toHaveAttribute("href", "/admin");
});

it("관리자는 관리자 등급으로 표시된다", async () => {
  renderMenu({ username: "ops", role: "operator", can_operate: true });
  expect(await screen.findByText("관리자")).toHaveAttribute("data-role", "operator");
});

it("로그아웃하면 서버 세션을 끊고 로그인 링크로 바뀐다", async () => {
  const fetch = renderMenu({ username: "kim", role: "viewer", can_operate: false });
  await userEvent.click(await screen.findByRole("button", { name: "로그아웃" }));
  expect(await screen.findByRole("link", { name: "로그인" })).toBeInTheDocument();
  expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/admin/auth/logout"))).toBe(true);
  await waitFor(() => expect(refresh).toHaveBeenCalled());
});
