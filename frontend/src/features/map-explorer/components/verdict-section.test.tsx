import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { RegionIndustryVerdict, VerdictSignal } from "@/shared/api/types";
import { ApiError } from "@/shared/api/client";
import * as api from "../api";
import { VerdictSection } from "./verdict-section";

const signal = (key: VerdictSignal["key"], level: VerdictSignal["level"], evidence: string): VerdictSignal => ({
  key, level, value: 0.1, percentile: level === "unavailable" ? null : 80, evidence, source: "store",
});

function verdict(code: RegionIndustryVerdict["verdict_code"], signals: VerdictSignal[]): RegionIndustryVerdict {
  return {
    basis: "permit",
    region_code: "1168064000", industry_id: "korean_food", verdict_code: code,
    strong_count: signals.filter((s) => s.key !== "shrinking" && s.level === "strong").length,
    on_count: signals.filter((s) => s.key !== "shrinking" && (s.level === "on" || s.level === "strong")).length,
    signals, computed_at: "2026-09-29T04:30:00+09:00",
  };
}

const FIVE = [
  signal("net_outflow", "on", "순유출 근거"),
  signal("survival_cliff", "strong", "생존 근거"),
  signal("early_closure", "off", "조기폐업 근거"),
  signal("saturation", "unavailable", "표본 부족 — 상주인구 900명"),
  signal("shrinking", "strong", "상권축소 근거"),
];

function renderSection() {
  vi.spyOn(api, "fetchVerdictAlternatives").mockResolvedValue({
    region_code: "1168064000", industry_id: "korean_food", neighborhood_type: "office",
    industries: [{ industry_id: "snack", industry_name: "분식", verdict_code: "clear", strong_count: 0, on_count: 0 }],
    regions: [],
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, retryDelay: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <VerdictSection regionCode="1168064000" industry="korean_food" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

it("켜진 판정 신호는 강함부터 원천 순서를 유지해 최대 세 개만 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("red", [
    signal("net_outflow", "on", "순유출 근거"),
    signal("survival_cliff", "strong", "생존 근거"),
    signal("early_closure", "on", "조기폐업 근거"),
    signal("saturation", "strong", "포화 근거"),
  ]));
  renderSection();
  expect(await screen.findByRole("status", { name: /비추천/ })).toBeInTheDocument();
  const fired = screen.getAllByTestId("fired-signal").map((el) => el.textContent);
  expect(fired).toHaveLength(3);
  expect(fired[0]).toContain("생존 절벽");
  expect(fired[1]).toContain("포화");
  expect(fired[2]).toContain("순유출");
  expect(fired[0]).toContain("인허가");
  expect(screen.getByText("생존 근거")).toHaveAttribute("title", "생존 근거");
  expect(screen.queryByText("조기폐업 근거")).toBeNull();
});

it("근거 보기 토글과 꺼진 신호의 상세 근거를 표시하지 않는다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("red", FIVE));
  renderSection();
  await screen.findByRole("status", { name: /비추천/ });
  expect(screen.queryByRole("button", { name: /근거 보기|근거 접기/ })).toBeNull();
  expect(screen.queryByText("표본 부족 — 상주인구 900명")).toBeNull();
});

it.each(["on", "strong"] as const)("상권 축소가 %s이면 판정 신호 밖 회색 참고 줄로 표시한다", async (level) => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("orange", [
    signal("shrinking", level, "서울시 상권변화지표 '상권축소' (2026년 2분기)"),
    signal("net_outflow", "on", "순유출 근거"),
  ]));
  renderSection();
  const advisory = await screen.findByText("참고: 서울시 상권변화지표 '상권축소' (2026년 2분기)");
  expect(advisory).toHaveClass("text-[var(--text-secondary)]");
  const fired = screen.getAllByTestId("fired-signal");
  expect(fired).toHaveLength(1);
  expect(fired[0]).toHaveTextContent("순유출");
  expect(fired[0].compareDocumentPosition(advisory) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it.each(["off", "unavailable"] as const)("상권 축소가 %s이면 참고 줄도 표시하지 않는다", async (level) => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("clear", [signal("shrinking", level, "상권축소 근거")]));
  renderSection();
  await screen.findByRole("status", { name: /경고 없음/ });
  expect(screen.queryByText(/참고:/)).toBeNull();
});

it("상권 축소만 켜져 있으면 경고 없음 안내와 참고 줄을 함께 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("clear", [signal("shrinking", "on", "상권축소 근거")]));
  renderSection();
  expect(await screen.findByText("서울 같은 업종 동네와 비교해 켜진 경고 신호가 없습니다.")).toBeInTheDocument();
  expect(screen.getByText("참고: 상권축소 근거")).toBeInTheDocument();
  expect(screen.queryAllByTestId("fired-signal")).toHaveLength(0);
});

it("경고 없음·보류 판정은 켜진 신호 목록 대신 한 줄 설명을 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("insufficient", FIVE.map((s) => ({ ...s, level: "unavailable" }))));
  renderSection();
  expect(await screen.findByRole("status", { name: /판정 보류/ })).toBeInTheDocument();
  expect(screen.queryAllByTestId("fired-signal")).toHaveLength(0);
  expect(screen.getByText("표본이 부족해 판정을 보류했습니다.")).toBeInTheDocument();
});

it.each(["convenience_store", "real_estate"])("판정 제외 업종 %s은 요청 없이 섹션을 그리지 않는다", (industry) => {
  const spy = vi.spyOn(api, "fetchVerdict");
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { container } = render(
    <QueryClientProvider client={client}>
      <VerdictSection regionCode="1168064000" industry={industry} />
    </QueryClientProvider>,
  );
  expect(container.querySelector("section")).toBeNull();
  expect(spy).not.toHaveBeenCalled();
});

it("판정이 없는 조합(404)은 섹션을 그리지 않는다", async () => {
  const spy = vi.spyOn(api, "fetchVerdict").mockRejectedValue(new ApiError("VERDICT_NOT_FOUND", "판정이 없습니다"));
  const { container } = renderSection();
  await waitFor(() => expect(spy).toHaveBeenCalled());
  await waitFor(() => expect(container.firstChild).toBeNull());
  expect(screen.queryByRole("alert")).toBeNull();
});

it("판정 대상 업종이 아닌 404(INDUSTRY_NOT_FOUND)도 섹션을 그리지 않는다", async () => {
  const spy = vi.spyOn(api, "fetchVerdict").mockRejectedValue(new ApiError("INDUSTRY_NOT_FOUND", "판정 대상 업종이 아닙니다"));
  const { container } = renderSection();
  await waitFor(() => expect(spy).toHaveBeenCalled());
  await waitFor(() => expect(container.firstChild).toBeNull());
  expect(screen.queryByRole("alert")).toBeNull();
});

it("그 외 오류는 한 줄 안내를 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockRejectedValue(new Error("network"));
  renderSection();
  expect(await screen.findByRole("alert")).toHaveTextContent("판정을 불러오지 못했습니다");
});

it("비추천·조건부 카드는 대안 줄을 붙인다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("red", FIVE));
  renderSection();
  expect(await screen.findByTestId("alt-industries")).toHaveTextContent("굳이 이 동네라면");
  expect(screen.getByTestId("alt-industries")).toHaveTextContent("분식");
});

it("경고 없음 카드는 대안을 요청하지 않는다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("clear", FIVE.map((s) => ({ ...s, level: "off" }))));
  renderSection();
  const spy = vi.mocked(api.fetchVerdictAlternatives);
  expect(await screen.findByRole("status", { name: /경고 없음/ })).toBeInTheDocument();
  await new Promise((r) => setTimeout(r, 0)); // 대안 컴포넌트가 마운트됐다면 이 틱에 queryFn이 돌았을 것
  expect(screen.queryByTestId("alt-industries")).toBeNull();
  expect(spy).not.toHaveBeenCalled();
});
