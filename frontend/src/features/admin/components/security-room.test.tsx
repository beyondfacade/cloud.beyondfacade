import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { initialIpBlocks, securityOverviewFixture } from "@/app/api/mock/admin-fixtures";
import { searchSecurityEvents } from "@/app/api/mock/admin-ops-fixtures";
import type { AdminMe } from "@/shared/api/types";
import * as api from "../api";
import { SecurityRoom } from "./security-room";
import { renderWithQuery } from "./test-utils";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/admin/security" }));

const VIEWER: AdminMe = { username: "viewer", role: "viewer", can_operate: false };
const OPERATOR: AdminMe = { username: "ops", role: "operator", can_operate: true };

beforeEach(() => {
  vi.spyOn(api, "fetchSecurityOverview").mockResolvedValue(securityOverviewFixture);
  vi.spyOn(api, "fetchIpBlocks").mockResolvedValue(initialIpBlocks);
});
afterEach(() => vi.restoreAllMocks());

it("요약 지표와 심각도 배지가 붙은 알림을 보여준다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  renderWithQuery(<SecurityRoom />);
  const summary = await screen.findByLabelText("보안 요약 (최근 24시간)");
  expect(within(summary).getByText("로그인 실패").nextSibling).toHaveTextContent("12");
  expect(screen.getByText("관리자 로그인 실패 12회 (15분)")).toBeInTheDocument();
  expect(screen.getByText("심각")).toBeInTheDocument();
});

it("조회 관리자에게는 차단 버튼 대신 권한 안내를 보여준다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  renderWithQuery(<SecurityRoom />);
  await screen.findByText("관리자 로그인 실패 12회 (15분)");
  expect(screen.queryByRole("button", { name: "24시간 차단" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /IP 차단/ }));
  expect(screen.getByRole("note")).toHaveTextContent("운영 관리자 권한");
  expect(screen.queryByRole("button", { name: "해제" })).not.toBeInTheDocument();
});

it("운영 관리자는 알림에서 바로 24시간 차단한다 — 사유는 알림 제목", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const create = vi.spyOn(api, "createIpBlock").mockResolvedValue({
    ip: "203.0.113.10", reason: "x", created_at: "2026-09-29T12:00:00+09:00", expires_at: null, created_by: "ops",
  });
  renderWithQuery(<SecurityRoom />);
  await userEvent.click(await screen.findByRole("button", { name: "24시간 차단" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith({
    ip: "203.0.113.10", reason: "관리자 로그인 실패 12회 (15분)", ttl_minutes: 1_440,
  }));
});

it("이벤트 탭은 종류·IP로 걸러 조회하고 더 보기로 다음 쪽을 이어 붙인다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  const search = vi.spyOn(api, "fetchSecurityEvents").mockImplementation(async (filter, beforeId) =>
    searchSecurityEvents(filter.kind, filter.ip || null, filter.hours, beforeId, 50));
  renderWithQuery(<SecurityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: /이벤트/ }));
  expect(await screen.findByText("50건 표시")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "더 보기" }));
  expect(await screen.findByText("72건 표시 · 끝")).toBeInTheDocument();
  expect(search).toHaveBeenLastCalledWith({ kind: null, ip: "", hours: 24 }, 23);

  await userEvent.selectOptions(screen.getByLabelText("종류"), "로그인 실패");
  await userEvent.type(screen.getByLabelText("IP"), "203.0.113.10");
  await userEvent.click(screen.getByRole("button", { name: "검색" }));
  await waitFor(() => expect(search).toHaveBeenLastCalledWith({ kind: "login_failed", ip: "203.0.113.10", hours: 24 }, null));
});

it("감사 로그 탭은 관리자 행위를 행위 종류로 걸러 보여준다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
  const audit = vi.spyOn(api, "fetchAuditPage").mockResolvedValue({
    items: [{ id: 3, occurred_at: "2026-09-29T12:00:00+09:00", action: "user.suspend", actor: "ops", target: "kim.analyst", detail: "", ip: "10.0.0.5" }],
    next_before_id: null,
  });
  renderWithQuery(<SecurityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: "감사 로그" }));
  expect(await screen.findByText("kim.analyst")).toBeInTheDocument();
  expect(within(screen.getByRole("table")).getByText("접속 정지")).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("행위"), "IP 차단");
  await waitFor(() => expect(audit).toHaveBeenLastCalledWith("ip_block.create", null));
});

it("운영 관리자는 차단 탭에서 기간을 골라 추가하고 해제할 수 있다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const create = vi.spyOn(api, "createIpBlock").mockResolvedValue(initialIpBlocks[0]);
  const remove = vi.spyOn(api, "deleteIpBlock").mockResolvedValue(undefined);
  renderWithQuery(<SecurityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: /IP 차단/ }));
  await userEvent.type(screen.getByLabelText("IP 주소"), "192.0.2.9");
  await userEvent.selectOptions(screen.getByLabelText("기간"), "무기한");
  await userEvent.click(screen.getByRole("button", { name: "차단 추가" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith({ ip: "192.0.2.9", reason: "", ttl_minutes: null }));
  await userEvent.click(screen.getByRole("button", { name: "해제" }));
  await waitFor(() => expect(remove).toHaveBeenCalledWith("198.51.100.7"));
});
