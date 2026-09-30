import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/client";
import { SESSION_QUERY_KEY } from "@/shared/auth/session";
import * as api from "../api";
import { LoginForm } from "./login-form";
import { renderWithQuery } from "./test-utils";

const replace = vi.fn();
let params: Record<string, string> = {};
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => ({ get: (key: string) => params[key] ?? null }),
}));

beforeEach(() => {
  vi.spyOn(api, "fetchProviders").mockResolvedValue({ google: false });
});

afterEach(() => {
  vi.restoreAllMocks();
  replace.mockReset();
  params = {};
});

async function submit(loginId: string, password: string) {
  await userEvent.type(screen.getByLabelText("아이디 또는 이메일"), loginId);
  await userEvent.type(screen.getByLabelText("비밀번호"), password);
  await userEvent.click(screen.getByRole("button", { name: "로그인" }));
}

it("로그인에 성공하면 헤더 세션을 채우고 next로 돌아간다", async () => {
  params = { next: "/admin/facility" };
  const me = { username: "kim", role: "viewer" as const, can_operate: false };
  const login = vi.spyOn(api, "login").mockResolvedValue(me);
  const { client } = renderWithQuery(<LoginForm />);
  await submit(" kim@example.com ", "correct horse");
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin/facility"));
  expect(login).toHaveBeenCalledWith("kim@example.com", "correct horse");
  expect(client.getQueryData(SESSION_QUERY_KEY)).toEqual(me);
});

it("외부 next는 무시하고 첫 화면으로 간다", async () => {
  params = { next: "https://evil.test" };
  vi.spyOn(api, "login").mockResolvedValue({ username: "ops", role: "operator", can_operate: true });
  renderWithQuery(<LoginForm />);
  await submit("ops", "pw");
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
});

it("실패하면 서버 메시지를 보여주고 비밀번호를 비운다", async () => {
  vi.spyOn(api, "login").mockRejectedValue(new ApiError("INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다."));
  renderWithQuery(<LoginForm />);
  await submit("ops", "wrong");
  expect(await screen.findByRole("alert")).toHaveTextContent("올바르지 않습니다");
  expect(screen.getByLabelText("비밀번호")).toHaveValue("");
  expect(replace).not.toHaveBeenCalled();
});

it("구글 왕복이 실패해 돌아오면 이유를 보여준다", () => {
  params = { error: "EMAIL_TAKEN" };
  renderWithQuery(<LoginForm />);
  expect(screen.getByRole("alert")).toHaveTextContent("이 이메일로 가입된 계정이 있습니다");
});

it("구글이 설정돼 있으면 돌아올 경로를 실은 구글 버튼이 보인다", async () => {
  params = { next: "/admin" };
  vi.spyOn(api, "fetchProviders").mockResolvedValue({ google: true });
  renderWithQuery(<LoginForm />);
  const google = await screen.findByRole("link", { name: "Google로 계속하기" });
  expect(google.getAttribute("href")).toMatch(/\/admin\/auth\/google\/start\?next=%2Fadmin$/);
});

it("구글이 설정되지 않으면 구글 버튼이 없다", async () => {
  renderWithQuery(<LoginForm />);
  await waitFor(() => expect(api.fetchProviders).toHaveBeenCalled());
  expect(screen.queryByRole("link", { name: "Google로 계속하기" })).not.toBeInTheDocument();
});

it("회원가입 링크는 돌아올 경로를 이어 준다", () => {
  params = { next: "/map" };
  renderWithQuery(<LoginForm />);
  expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute("href", "/signup?next=%2Fmap");
});
