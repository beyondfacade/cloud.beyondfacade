import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import type { AdminMe } from "@/shared/api/types";
import { MyPage } from "./my-page";

afterEach(() => vi.unstubAllGlobals());

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });
const VIEWER: AdminMe = { id: 2, username: "kim", role: "viewer", can_operate: false, specialty: null, avatar_version: null };
const EXPERT: AdminMe = { id: 9, username: "lee", role: "expert", can_operate: false, specialty: "부동산", avatar_version: 3 };

function renderPage(me: AdminMe | null, respond: (url: string, init?: RequestInit) => Response = () => json(500, {})) {
  const fetch = vi.fn((url: string, init?: RequestInit) =>
    Promise.resolve(
      url.endsWith("/admin/auth/me")
        ? me ? json(200, me) : json(401, { error: { code: "UNAUTHENTICATED", message: "로그인이 필요합니다." } })
        : respond(url, init),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MyPage /></QueryClientProvider>);
  return fetch;
}

it("비로그인이면 마이페이지로 돌아오는 로그인 링크를 보여준다", async () => {
  renderPage(null);
  expect(await screen.findByRole("link", { name: "로그인" })).toHaveAttribute("href", "/login?next=%2Fmypage");
});

it("사진을 고르면 이미지 바이트를 그대로 올리고 새 사진으로 바꿔 보여준다", async () => {
  const fetch = renderPage(VIEWER, () => json(200, { ...VIEWER, avatar_version: 1 }));
  await screen.findByText("kim · 일반");
  expect(screen.queryByRole("combobox", { name: "전문 업종" })).not.toBeInTheDocument();

  const photo = new File(["png"], "me.png", { type: "image/png" });
  await userEvent.upload(screen.getByLabelText("프로필 사진 파일"), photo);

  expect(await screen.findByRole("img", { name: "내 프로필 사진" })).toHaveAttribute("src", "/api/mock/admin/auth/avatars/2?v=1");
  const [url, init] = fetch.mock.calls.find(([u]) => u.endsWith("/admin/auth/avatar"))!;
  expect(url).toBe("/api/mock/admin/auth/avatar");
  expect(init).toMatchObject({ method: "PUT", body: photo, headers: { "Content-Type": "image/png" } });
});

it("1MB가 넘거나 이미지가 아니면 올리지 않고 알려준다", async () => {
  const fetch = renderPage(VIEWER);
  const input = await screen.findByLabelText("프로필 사진 파일");
  await userEvent.upload(input, new File([new Uint8Array(1024 * 1024 + 1)], "big.png", { type: "image/png" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("1MB 이하");
  expect(fetch.mock.calls.some(([u]) => u.endsWith("/admin/auth/avatar"))).toBe(false);
});

it("전문가는 지금 업종(목록에 없어도)을 보고 다른 업종으로 저장한다", async () => {
  const fetch = renderPage(EXPERT, (_url, init) => json(200, { ...EXPERT, specialty: JSON.parse(String(init?.body)).specialty }));
  const select = await screen.findByRole("combobox", { name: "전문 업종" });
  expect(select).toHaveValue("부동산");
  expect(screen.getByRole("img", { name: "내 프로필 사진" })).toHaveAttribute("src", "/api/mock/admin/auth/avatars/9?v=3");

  await userEvent.selectOptions(select, "카페");
  await userEvent.click(screen.getByRole("button", { name: "저장" }));

  expect(await screen.findByRole("status")).toHaveTextContent("저장했어요");
  const [, init] = fetch.mock.calls.find(([u]) => u.endsWith("/admin/auth/specialty"))!;
  expect(JSON.parse(String(init?.body))).toEqual({ specialty: "카페" });
});
