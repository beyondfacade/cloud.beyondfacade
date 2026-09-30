import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { facilitySnapshotFixture } from "@/app/api/mock/admin-fixtures";
import * as api from "../api";
import { FacilityRoom } from "./facility-room";
import { renderWithQuery } from "./test-utils";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/admin/facility" }));

afterEach(() => vi.restoreAllMocks());

it("자원 게이지는 사용률을 계산해 보여준다 — 메모리 26/64GB는 40.6%", async () => {
  vi.spyOn(api, "fetchFacilitySnapshot").mockResolvedValue(facilitySnapshotFixture);
  renderWithQuery(<FacilityRoom />);
  expect(await screen.findByRole("meter", { name: "메모리" })).toHaveAttribute("aria-valuenow", "40.6");
  expect(screen.getByRole("meter", { name: "디스크 /" })).toHaveAttribute("aria-valuenow", "61.2");
  expect(screen.getByText("metabole-dev")).toBeInTheDocument();
});

it("수집기 탭은 지연·누락 수를 배지로 달고 상태를 한국어로 보여준다", async () => {
  vi.spyOn(api, "fetchFacilitySnapshot").mockResolvedValue(facilitySnapshotFixture);
  renderWithQuery(<FacilityRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: /수집기\s*2/ }));
  expect(screen.getByText("지연")).toBeInTheDocument();
  expect(screen.getAllByText("기록 없음").length).toBeGreaterThan(0);
  // 상대 시각 기준은 스냅샷 generated_at(12:00:00) — 뉴스 폴러 11:00:05 실행은 59분 전
  expect(screen.getByText("59분 전")).toBeInTheDocument();
});

it("GPU가 없고 DB에 닿지 않아도 화면이 무너지지 않는다", async () => {
  vi.spyOn(api, "fetchFacilitySnapshot").mockResolvedValue({ ...facilitySnapshotFixture, gpus: [], database: null });
  renderWithQuery(<FacilityRoom />);
  expect(await screen.findByText(/감지된 GPU가 없습니다/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "데이터베이스" }));
  expect(screen.getByText("데이터베이스에 연결할 수 없습니다.")).toBeInTheDocument();
});
