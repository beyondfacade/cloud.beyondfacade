import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { facilitySnapshotFixture } from "@/app/api/mock/admin-fixtures";
import { collectorLogFixture, hostHistoryFixture } from "@/app/api/mock/admin-ops-fixtures";
import { ApiError } from "@/shared/api/client";
import type { AdminMe } from "@/shared/api/types";
import * as api from "../api";
import { FacilityRoom } from "./facility-room";
import { renderWithQuery } from "./test-utils";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/admin/facility" }));

const VIEWER: AdminMe = { username: "viewer", role: "viewer", can_operate: false };
const OPERATOR: AdminMe = { username: "ops", role: "operator", can_operate: true };

beforeEach(() => {
  vi.spyOn(api, "fetchFacilitySnapshot").mockResolvedValue(facilitySnapshotFixture);
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(VIEWER);
});
afterEach(() => vi.restoreAllMocks());

it("자원 게이지는 사용률을 계산해 보여준다 — 메모리 26/64GB는 40.6%", async () => {
  renderWithQuery(<FacilityRoom />);
  expect(await screen.findByRole("meter", { name: "메모리" })).toHaveAttribute("aria-valuenow", "40.6");
  expect(screen.getByRole("meter", { name: "디스크 /" })).toHaveAttribute("aria-valuenow", "61.2");
  expect(screen.getByText("metabole-dev")).toBeInTheDocument();
});

it("수집기 탭은 지연·누락 수를 배지로 달고 상태를 한국어로 보여준다", async () => {
  renderWithQuery(<FacilityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: /수집기\s*2/ }));
  expect(screen.getByText("지연")).toBeInTheDocument();
  expect(screen.getAllByText("기록 없음").length).toBeGreaterThan(0);
  // 상대 시각 기준은 스냅샷 generated_at(12:00:00) — 뉴스 폴러 11:00:05 실행은 59분 전
  expect(screen.getByText("59분 전")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /로그$/ })).not.toBeInTheDocument();
});

it("GPU가 없고 DB에 닿지 않아도 화면이 무너지지 않는다", async () => {
  vi.spyOn(api, "fetchFacilitySnapshot").mockResolvedValue({ ...facilitySnapshotFixture, gpus: [], database: null });
  renderWithQuery(<FacilityRoom />);
  expect(await screen.findByText(/감지된 GPU가 없습니다/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "데이터베이스" }));
  expect(screen.getByText("데이터베이스에 연결할 수 없습니다.")).toBeInTheDocument();
});

it("추세 탭은 서버 표본 이력을 그리고 기간을 바꾸면 다시 조회한다", async () => {
  const history = vi.spyOn(api, "fetchHostHistory").mockImplementation(async (hours) => hostHistoryFixture(hours));
  renderWithQuery(<FacilityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: "추세" }));
  expect(await screen.findByRole("img", { name: "CPU·메모리·디스크 사용률" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "GPU 온도" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "7일" }));
  await waitFor(() => expect(history).toHaveBeenLastCalledWith(168));
});

it("운영 관리자는 수집기 로그를 열고, 이미 실행 중이면 409 안내를 본다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue(OPERATOR);
  const log = vi.spyOn(api, "fetchCollectorLog").mockImplementation(async (key, lines) => collectorLogFixture(key, lines ?? 200, false));
  const run = vi.spyOn(api, "runCollector").mockRejectedValue(new ApiError("COLLECTOR_RUNNING", "이미 실행 중인 수집기입니다."));
  renderWithQuery(<FacilityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: /수집기/ }));
  const [first] = facilitySnapshotFixture.collectors;
  await userEvent.click(await screen.findByRole("button", { name: `${first.label} 로그` }));
  const section = await screen.findByRole("region", { name: `${first.label} 로그` });
  expect(await within(section).findByText(/serviceKey=\*\*\*/)).toBeInTheDocument();
  expect(log).toHaveBeenCalledWith(first.key, 200);

  await userEvent.click(within(section).getByRole("button", { name: "지금 실행" }));
  await waitFor(() => expect(run).toHaveBeenCalledWith(first.key));
  expect(await within(section).findByRole("alert")).toHaveTextContent("이미 실행 중");
});
