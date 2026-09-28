import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
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
    region_code: "1168064000", industry_id: "korean_food", verdict_code: code,
    strong_count: signals.filter((s) => s.level === "strong").length,
    on_count: signals.filter((s) => s.level === "on" || s.level === "strong").length,
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
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <VerdictSection regionCode="1168064000" industry="korean_food" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

it("판정 배지와 켜진 신호를 강함 먼저 보여주고, 근거 보기를 펼치면 5개 전부 나온다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("red", FIVE));
  renderSection();
  expect(await screen.findByRole("status", { name: /비추천/ })).toBeInTheDocument();
  const fired = screen.getAllByTestId("fired-signal").map((el) => el.textContent);
  expect(fired[0]).toContain("생존 절벽");
  expect(fired[1]).toContain("상권 축소");
  expect(fired[2]).toContain("순유출");
  expect(fired).toHaveLength(3);
  expect(screen.queryByText("표본 부족 — 상주인구 900명")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /근거 보기/ }));
  expect(screen.getByText("표본 부족 — 상주인구 900명")).toBeInTheDocument();
  expect(screen.getAllByTestId("all-signal")).toHaveLength(5);
});

it("경고 없음·보류 판정은 켜진 신호 목록 대신 한 줄 설명을 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("insufficient", FIVE.map((s) => ({ ...s, level: "unavailable" }))));
  renderSection();
  expect(await screen.findByRole("status", { name: /판정 보류/ })).toBeInTheDocument();
  expect(screen.queryAllByTestId("fired-signal")).toHaveLength(0);
  expect(screen.getByText(/표본 부족/)).toBeInTheDocument();
});

it("판정 제외 업종(편의점)은 요청 없이 섹션을 그리지 않는다", () => {
  const spy = vi.spyOn(api, "fetchVerdict");
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { container } = render(
    <QueryClientProvider client={client}>
      <VerdictSection regionCode="1168064000" industry="convenience_store" />
    </QueryClientProvider>,
  );
  expect(container.querySelector("section")).toBeNull();
  expect(spy).not.toHaveBeenCalled();
});

it("판정이 없는 조합(404)은 섹션을 그리지 않는다", async () => {
  vi.spyOn(api, "fetchVerdict").mockRejectedValue(new ApiError("VERDICT_NOT_FOUND", "판정이 없습니다"));
  const { container } = renderSection();
  await new Promise((r) => setTimeout(r, 0));
  expect(container.querySelector("section")).toBeNull();
});

it("그 외 오류는 한 줄 안내를 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockRejectedValue(new Error("network"));
  renderSection();
  expect(await screen.findByRole("alert")).toHaveTextContent("판정을 불러오지 못했습니다");
});
