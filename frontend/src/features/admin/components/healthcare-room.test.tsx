import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { healthcareSnapshotFixture, probeFixture } from "@/app/api/mock/admin-fixtures";
import { usageSeriesFixture } from "@/app/api/mock/admin-ops-fixtures";
import * as api from "../api";
import { formatRate } from "../lib/format";
import { HealthcareRoom } from "./healthcare-room";
import { renderWithQuery } from "./test-utils";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/admin/healthcare" }));

beforeEach(() => {
  vi.spyOn(api, "fetchHealthcareSnapshot").mockResolvedValue(healthcareSnapshotFixture);
  vi.spyOn(api, "fetchUsageSeries").mockImplementation(async (hours) => usageSeriesFixture(hours as 24 | 168));
});
afterEach(() => vi.restoreAllMocks());

it("LLM 체인은 1차·폴백 순서로, 필수 모델은 적재 상태로 보여준다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "viewer", role: "viewer", can_operate: false });
  renderWithQuery(<HealthcareRoom />);
  const chain = await screen.findByRole("region", { name: "분석 LLM 체인" });
  expect(chain).toHaveTextContent(/1차.*gemini-2\.5-flash.*폴백.*gemma4:12b/s);
  expect(screen.getByText("메모리 적재")).toBeInTheDocument();
});

it("사용량 탭은 24시간·7일 창을 전환한다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "viewer", role: "viewer", can_operate: false });
  renderWithQuery(<HealthcareRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: "사용량" }));
  expect(screen.getByLabelText("LLM 사용량 (24h)")).toHaveTextContent("14");
  await userEvent.click(screen.getByRole("button", { name: "7일" }));
  expect(screen.getByLabelText("LLM 사용량 (7d)")).toHaveTextContent("61");
  expect(screen.getByText("학원")).toBeInTheDocument();
});

it("사용량 탭은 폴백률·오류율과 시간대별 분석 차트를 보여준다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "viewer", role: "viewer", can_operate: false });
  renderWithQuery(<HealthcareRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: "사용량" }));
  const outcomes = usageSeriesFixture(24).outcomes;
  const strip = await screen.findByLabelText("LLM 호출 결과");
  expect(within(strip).getByText("폴백률").nextSibling).toHaveTextContent(formatRate(outcomes.fallback_rate));
  expect(within(strip).getByText("오류율").nextSibling).toHaveTextContent(formatRate(outcomes.error_rate));
  expect(screen.getByRole("img", { name: "LLM 호출 결과 추이" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "시간대별 분석 건수" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "7일" }));
  await waitFor(() => expect(api.fetchUsageSeries).toHaveBeenLastCalledWith(168));
});

it("일반 회원은 프로브를 실행할 수 없다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "viewer", role: "viewer", can_operate: false });
  renderWithQuery(<HealthcareRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: "프로브" }));
  expect(screen.getByRole("note")).toHaveTextContent("관리자만");
});

it("운영 관리자는 RAG 프로브를 돌려 점수 순 검색 결과를 본다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockResolvedValue({ username: "ops", role: "operator", can_operate: true });
  const probe = vi.spyOn(api, "runProbe").mockResolvedValue(probeFixture("rag", "임대료"));
  renderWithQuery(<HealthcareRoom />);
  await userEvent.click(await screen.findByRole("tab", { name: "프로브" }));
  await userEvent.type(screen.getByLabelText("프로브 질의"), "임대료");
  await userEvent.click(screen.getByRole("button", { name: "프로브 실행" }));
  await waitFor(() => expect(probe).toHaveBeenCalledWith("rag", "임대료"));
  expect(await screen.findByText("0.812")).toBeInTheDocument();
});
