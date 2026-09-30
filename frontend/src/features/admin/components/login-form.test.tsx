import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/client";
import * as api from "../api";
import { LoginForm } from "./login-form";
import { renderWithQuery } from "./test-utils";

const replace = vi.fn();
let next: string | null = null;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => ({ get: () => next }),
}));

afterEach(() => {
  vi.restoreAllMocks();
  replace.mockReset();
  next = null;
});

async function submit(username: string, password: string) {
  await userEvent.type(screen.getByLabelText("아이디"), username);
  await userEvent.type(screen.getByLabelText("비밀번호"), password);
  await userEvent.click(screen.getByRole("button", { name: "들어가기" }));
}

it("로그인에 성공하면 next로 돌아간다", async () => {
  next = "/admin/facility";
  const login = vi.spyOn(api, "loginAdmin").mockResolvedValue({ username: "ops", role: "operator", can_operate: true });
  renderWithQuery(<LoginForm />);
  await submit(" ops ", "correct horse");
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin/facility"));
  expect(login).toHaveBeenCalledWith("ops", "correct horse");
});

it("외부 next는 무시하고 허브로 간다", async () => {
  next = "https://evil.test";
  vi.spyOn(api, "loginAdmin").mockResolvedValue({ username: "ops", role: "operator", can_operate: true });
  renderWithQuery(<LoginForm />);
  await submit("ops", "pw");
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin"));
});

it("실패하면 서버 메시지를 보여주고 비밀번호를 비운다", async () => {
  vi.spyOn(api, "loginAdmin").mockRejectedValue(new ApiError("INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다."));
  renderWithQuery(<LoginForm />);
  await submit("ops", "wrong");
  expect(await screen.findByRole("alert")).toHaveTextContent("올바르지 않습니다");
  expect(screen.getByLabelText("비밀번호")).toHaveValue("");
  expect(replace).not.toHaveBeenCalled();
});
