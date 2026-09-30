import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/client";
import { SESSION_QUERY_KEY } from "@/shared/auth/session";
import * as api from "../api";
import { SignupForm } from "./signup-form";
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

async function fill({ username = "Kim.Dev", email = "kim@example.com", password = "long-enough-pw", confirm = password } = {}) {
  await userEvent.type(screen.getByLabelText("아이디"), username);
  await userEvent.type(screen.getByLabelText("이메일"), email);
  await userEvent.type(screen.getByLabelText("비밀번호"), password);
  await userEvent.type(screen.getByLabelText("비밀번호 확인"), confirm);
  await userEvent.click(screen.getByRole("button", { name: "가입하기" }));
}

it("가입하면 일반 회원으로 로그인된 채 next로 간다 — 아이디는 소문자로 받는다", async () => {
  params = { next: "/admin" };
  const me = { username: "kim.dev", role: "viewer" as const, can_operate: false };
  const signup = vi.spyOn(api, "signup").mockResolvedValue(me);
  const { client } = renderWithQuery(<SignupForm />);
  await fill();
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin"));
  expect(signup).toHaveBeenCalledWith({ username: "kim.dev", email: "kim@example.com", password: "long-enough-pw" });
  expect(client.getQueryData(SESSION_QUERY_KEY)).toEqual(me);
});

it("비밀번호 확인이 다르면 서버에 보내지 않는다", async () => {
  const signup = vi.spyOn(api, "signup");
  renderWithQuery(<SignupForm />);
  await fill({ confirm: "something-else" });
  expect(screen.getByRole("alert")).toHaveTextContent("비밀번호가 서로 다릅니다.");
  expect(signup).not.toHaveBeenCalled();
});

it("서버가 거절하면 이유를 보여준다", async () => {
  vi.spyOn(api, "signup").mockRejectedValue(new ApiError("EMAIL_TAKEN", "이미 가입된 이메일입니다."));
  renderWithQuery(<SignupForm />);
  await fill();
  expect(await screen.findByRole("alert")).toHaveTextContent("이미 가입된 이메일입니다.");
  expect(replace).not.toHaveBeenCalled();
});

it("로그인 링크는 돌아올 경로를 이어 준다", () => {
  params = { next: "/admin/users" };
  renderWithQuery(<SignupForm />);
  expect(screen.getByRole("link", { name: "로그인" })).toHaveAttribute("href", "/login?next=%2Fadmin%2Fusers");
});
