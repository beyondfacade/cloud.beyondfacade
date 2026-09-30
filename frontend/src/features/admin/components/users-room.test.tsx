import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { accounts, sessionsFor } from "@/app/api/mock/admin/users/store";
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
beforeEach(() => {
  search.value = new URLSearchParams();
  listCalls = [];
  vi.spyOn(api, "fetchAdminUsers").mockImplementation(async (filter) => {
    listCalls.push(filter);
    const items = USERS.filter((u) => filter.status === "all" || (filter.status === "active") === u.is_active)
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

it("관리자는 다른 계정의 등급을 바꾸고, 확인을 거쳐 접속을 정지한다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const role = vi.spyOn(api, "changeAdminRole").mockResolvedValue({ ...USERS[2], role: "viewer" });
  const status = vi.spyOn(api, "setAdminActive").mockResolvedValue({ ...USERS[2], is_active: false });
  renderWithQuery(<UsersRoom />);
  await userEvent.click(await screen.findByRole("button", { name: "lee.ops" }));
  const panel = screen.getByRole("region", { name: "계정 lee.ops" });
  await userEvent.click(within(within(panel).getByRole("group", { name: "등급 변경" })).getByRole("button", { name: "일반" }));
  await waitFor(() => expect(role).toHaveBeenCalledWith("lee.ops", "viewer"));
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

it("관리자는 12자 이상 초기 비밀번호로 계정을 추가한다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const create = vi.spyOn(api, "createAdminUser").mockResolvedValue({
    username: "park.ops", role: "operator", is_active: true, created_at: null, last_login_at: null, active_sessions: 0,
    email: null, has_password: true, has_google: false,
  });
  renderWithQuery(<UsersRoom />);
  await userEvent.click(await screen.findByRole("button", { name: "계정 추가" }));
  const form = screen.getByRole("form", { name: "계정 추가" });
  await userEvent.type(within(form).getByLabelText("아이디"), "park.ops");
  await userEvent.selectOptions(within(form).getByLabelText("등급"), "관리자");
  await userEvent.type(within(form).getByLabelText("초기 비밀번호"), "short");
  expect(within(form).getByRole("button", { name: "계정 만들기" })).toBeDisabled();
  await userEvent.type(within(form).getByLabelText("초기 비밀번호"), "-but-long-now");
  await userEvent.click(within(form).getByRole("button", { name: "계정 만들기" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith({ username: "park.ops", role: "operator", password: "short-but-long-now" }));
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

it("구글로만 가입한 본인 계정은 비밀번호 변경 대신 안내를 본다", async () => {
  search.value = new URLSearchParams("user=kim.analyst");
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "kim.analyst", role: "viewer", can_operate: false });
  renderWithQuery(<UsersRoom />);
  const panel = await screen.findByRole("region", { name: "계정 kim.analyst" });
  expect(within(panel).queryByRole("form", { name: "내 비밀번호 변경" })).not.toBeInTheDocument();
  expect(within(panel).getByText(/구글로 가입한 계정이라 비밀번호가 없습니다/)).toBeInTheDocument();
});
