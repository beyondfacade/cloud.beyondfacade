import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { accounts, sessionsFor } from "@/app/api/mock/admin/users/store";
import { ApiError } from "@/shared/api/client";
import type { AdminMe, AdminUserFilter } from "@/shared/api/types";
import * as api from "../api";
import { UsersRoom } from "./users-room";
import { renderWithQuery } from "./test-utils";

const search = { value: new URLSearchParams() };
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/admin/users",
  useSearchParams: () => search.value,
}));

const VIEWER: AdminMe = { username: "viewer", role: "viewer", can_operate: false };
const OPERATOR: AdminMe = { username: "ops", role: "operator", can_operate: true };
const USERS = [...accounts.values()].map((a) => a.user);

let listCalls: AdminUserFilter[] = [];
let users = USERS;
beforeEach(() => {
  search.value = new URLSearchParams();
  listCalls = [];
  users = USERS;
  vi.spyOn(api, "fetchAdminUsers").mockImplementation(async (filter) => {
    listCalls.push(filter);
    const items = users.filter((u) => filter.status === "all" || (filter.status === "active") === u.is_active)
      .filter((u) => !filter.role || u.role === filter.role)
      .filter((u) => u.username.includes(filter.q.trim()));
    return { items };
  });
  vi.spyOn(api, "fetchAdminSessions").mockImplementation(async (username) => ({ items: sessionsFor(username, "ops") }));
});
afterEach(() => vi.restoreAllMocks());

it("요약 지표에 정지 계정 수를 보이고, 일반 회원은 상세 패널에서 변경 권한 안내만 본다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  renderWithQuery(<UsersRoom />);
  const summary = await screen.findByLabelText("계정 요약");
  expect(within(summary).getByText("접속 정지").nextSibling).toHaveTextContent("1명");
  expect(screen.queryByRole("button", { name: "계정 추가" })).not.toBeInTheDocument();
  await userEvent.click(await screen.findByRole("button", { name: "lee.ops" }));
  const panel = screen.getByRole("region", { name: "계정 lee.ops" });
  expect(within(panel).getByRole("note")).toHaveTextContent("관리자 권한");
  expect(within(panel).queryByRole("group", { name: "등급 변경" })).not.toBeInTheDocument();
});

it("상태 필터를 고르면 서버 필터로 다시 조회한다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  renderWithQuery(<UsersRoom />);
  await userEvent.click(await screen.findByRole("button", { name: "정지" }));
  await waitFor(() => expect(listCalls).toContainEqual({ q: "", role: null, status: "suspended" }));
  expect(await screen.findByRole("button", { name: "kim.analyst" })).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole("button", { name: "lee.ops" })).not.toBeInTheDocument());
});

it("관리자는 남의 등급·비밀번호를 바꿀 수 없고, 확인을 거쳐 접속만 정지한다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const status = vi.spyOn(api, "setAdminActive").mockResolvedValue({ ...USERS[2], is_active: false });
  renderWithQuery(<UsersRoom />);
  expect(await screen.findByLabelText("계정 요약")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "계정 추가" })).not.toBeInTheDocument();
  await userEvent.click(await screen.findByRole("button", { name: "lee.ops" }));
  const panel = screen.getByRole("region", { name: "계정 lee.ops" });
  expect(within(panel).getByRole("note")).toHaveTextContent("다른 회원의 등급과 비밀번호는 바꿀 수 없습니다");
  expect(within(panel).queryByRole("group", { name: "등급 변경" })).not.toBeInTheDocument();
  expect(within(panel).queryByRole("form", { name: "비밀번호 재설정" })).not.toBeInTheDocument();
  expect(within(panel).queryByLabelText("새 비밀번호")).not.toBeInTheDocument();
  await userEvent.click(within(panel).getByRole("button", { name: "접속 정지" }));
  expect(status).not.toHaveBeenCalled();
  await userEvent.click(within(panel).getByRole("button", { name: "정지 확인" }));
  await waitFor(() => expect(status).toHaveBeenCalledWith("lee.ops", false));
});

it("주소의 ?user=가 본인이면 등급 변경 대신 내 비밀번호 변경 폼을 연다", async () => {
  search.value = new URLSearchParams("user=ops");
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const change = vi.spyOn(api, "changeMyPassword").mockResolvedValue(undefined);
  renderWithQuery(<UsersRoom />);
  const panel = await screen.findByRole("region", { name: "계정 ops" });
  expect(within(panel).queryByRole("group", { name: "등급 변경" })).not.toBeInTheDocument();
  expect(await within(panel).findByText("현재 세션")).toBeInTheDocument();
  expect(within(panel).getByRole("button", { name: "다른 세션 모두 끊기" })).toBeEnabled();

  const form = within(panel).getByRole("form", { name: "내 비밀번호 변경" });
  await userEvent.type(within(form).getByLabelText("현재 비밀번호"), "old-password-1");
  await userEvent.type(within(form).getByLabelText("새 비밀번호"), "brand-new-pass-1");
  await userEvent.type(within(form).getByLabelText("새 비밀번호 확인"), "brand-new-pass-2");
  expect(within(form).getByText("새 비밀번호가 서로 다릅니다.")).toBeInTheDocument();
  expect(within(form).getByRole("button", { name: "비밀번호 변경" })).toBeDisabled();

  await userEvent.clear(within(form).getByLabelText("새 비밀번호 확인"));
  await userEvent.type(within(form).getByLabelText("새 비밀번호 확인"), "brand-new-pass-1");
  await userEvent.click(within(form).getByRole("button", { name: "비밀번호 변경" }));
  await waitFor(() => expect(change).toHaveBeenCalledWith("old-password-1", "brand-new-pass-1"));
});

it("본인은 계정명을 바꾸고, 패널은 새 이름으로 이어서 열려 있다", async () => {
  search.value = new URLSearchParams("user=viewer");
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  const rename = vi.spyOn(api, "changeMyUsername").mockImplementation(async (username) => {
    users = users.map((u) => (u.username === "viewer" ? { ...u, username } : u));
    return { ...VIEWER, username };
  });
  renderWithQuery(<UsersRoom />);
  const panel = await screen.findByRole("region", { name: "계정 viewer" });
  const form = within(panel).getByRole("form", { name: "내 계정명 변경" });
  const input = within(form).getByLabelText("새 계정명");
  expect(within(form).getByRole("button", { name: "계정명 변경" })).toBeDisabled();

  await userEvent.clear(input);
  await userEvent.type(input, "Bad Name");
  expect(within(form).getByText(/계정명은 영문 소문자/)).toBeInTheDocument();
  expect(within(form).getByRole("button", { name: "계정명 변경" })).toBeDisabled();

  await userEvent.clear(input);
  await userEvent.type(input, "viewer.kim");
  await userEvent.click(within(form).getByRole("button", { name: "계정명 변경" }));
  await waitFor(() => expect(rename).toHaveBeenCalledWith("viewer.kim"));
  const renamed = await screen.findByRole("region", { name: "계정 viewer.kim" });
  expect(within(renamed).getByRole("status")).toHaveTextContent("계정명을 바꿨습니다");
  expect(screen.getByRole("button", { name: "viewer.kim" }).closest("tr")).toHaveTextContent("나");
});

it("계정명이 이미 있으면 서버 오류 문구를 보여준다", async () => {
  search.value = new URLSearchParams("user=viewer");
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  vi.spyOn(api, "changeMyUsername").mockRejectedValue(new ApiError("USERNAME_TAKEN", "이미 있는 계정명입니다: ops"));
  renderWithQuery(<UsersRoom />);
  const form = within(await screen.findByRole("region", { name: "계정 viewer" })).getByRole("form", { name: "내 계정명 변경" });
  await userEvent.clear(within(form).getByLabelText("새 계정명"));
  await userEvent.type(within(form).getByLabelText("새 계정명"), "ops");
  await userEvent.click(within(form).getByRole("button", { name: "계정명 변경" }));
  expect(await within(form).findByRole("alert")).toHaveTextContent("이미 있는 계정명입니다: ops");
});

it("목록은 이메일과 가입 방식을 보여준다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  renderWithQuery(<UsersRoom />);
  const row = (await screen.findByRole("button", { name: "kim.analyst" })).closest("tr")!;
  expect(within(row).getByText("kim.analyst@gmail.com")).toBeInTheDocument();
  expect(within(row).getByText("구글")).toBeInTheDocument();
  const both = screen.getByRole("button", { name: "lee.ops" }).closest("tr")!;
  expect(within(both).getByText("비밀번호 · 구글")).toBeInTheDocument();
});

it("구글로만 가입한 본인 계정은 현재 비밀번호 없이 비밀번호를 처음 설정한다", async () => {
  search.value = new URLSearchParams("user=kim.analyst");
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "kim.analyst", role: "viewer", can_operate: false });
  const change = vi.spyOn(api, "changeMyPassword").mockResolvedValue(undefined);
  renderWithQuery(<UsersRoom />);
  const panel = await screen.findByRole("region", { name: "계정 kim.analyst" });
  expect(within(panel).queryByRole("form", { name: "내 비밀번호 변경" })).not.toBeInTheDocument();
  const form = within(panel).getByRole("form", { name: "비밀번호 설정" });
  expect(within(form).queryByLabelText("현재 비밀번호")).not.toBeInTheDocument();
  await userEvent.type(within(form).getByLabelText("새 비밀번호"), "brand-new-pass-1");
  await userEvent.type(within(form).getByLabelText("새 비밀번호 확인"), "brand-new-pass-1");
  await userEvent.click(within(form).getByRole("button", { name: "비밀번호 설정" }));
  await waitFor(() => expect(change).toHaveBeenCalledWith("", "brand-new-pass-1"));
  expect(await within(form).findByRole("status")).toHaveTextContent("설정했습니다");
});

it("scrollIntoView가 Promise를 돌려주는 브라우저에서도 패널을 열고 닫을 수 있다", async () => {
  const scroll = vi.fn(() => Promise.resolve());
  Object.defineProperty(Element.prototype, "scrollIntoView", { value: scroll, configurable: true, writable: true });
  try {
    vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
    renderWithQuery(<UsersRoom />);
    await userEvent.click(await screen.findByRole("button", { name: "lee.ops" }));
    const panel = screen.getByRole("region", { name: "계정 lee.ops" });
    expect(scroll).toHaveBeenCalled();
    await userEvent.click(within(panel).getByRole("button", { name: "닫기" }));
    expect(screen.queryByRole("region", { name: "계정 lee.ops" })).not.toBeInTheDocument();
  } finally {
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
  }
});
