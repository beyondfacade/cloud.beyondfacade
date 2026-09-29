import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { VerdictSignal } from "@/shared/api/types";
import { VerdictCard } from "./verdict-card";

it("훅 없이 판정 배지와 산출일을 표시한다", () => {
  render(<VerdictCard industryLabel="카페" verdict={{ region_code: "1", industry_id: "cafe", basis: "permit", verdict_code: "clear", strong_count: 0, on_count: 0, signals: [], computed_at: "2026-09-29T04:30:00+09:00" }} />);
  expect(screen.getByRole("status", { name: "카페 판정: 경고 없음" })).toBeInTheDocument();
  expect(screen.getByText("2026-09-29", { selector: "time" }).parentElement).toHaveTextContent("산출일 2026-09-29");
});

const signal = (over: Partial<VerdictSignal>): VerdictSignal => ({
  key: "net_outflow", level: "off", value: 0, percentile: 10, evidence: "근거", source: "store", ...over,
});
const base = { region_code: "1", industry_id: "real_estate", verdict_code: "orange" as const, strong_count: 0, on_count: 1, computed_at: "2026-09-29T04:30:00+09:00" };

it("집계 기반 판정은 배지와 설명 툴팁을 단다", () => {
  render(<VerdictCard industryLabel="부동산중개업" verdict={{ ...base, basis: "aggregate", signals: [signal({ key: "closure_rate", level: "on", source: "commerce", evidence: "지난 4분기 폐업 18곳" })] }} />);
  const badge = screen.getByText("집계 기반 판정");
  expect(badge).toHaveAttribute("title", expect.stringContaining("서울시 상권분석"));
  expect(screen.getByText("상권분석 집계")).toBeInTheDocument(); // 원천 태그
});

it("인허가 판정은 원천 배지가 없다", () => {
  render(<VerdictCard industryLabel="한식" verdict={{ ...base, industry_id: "korean_food", basis: "permit", signals: [] }} />);
  expect(screen.queryByText("집계 기반 판정")).toBeNull();
  expect(screen.queryByText("담배소매인 이력 기준")).toBeNull();
});

it("켜진 참고 신호가 둘이면 참고 줄도 둘이다", () => {
  render(<VerdictCard industryLabel="편의점" verdict={{ ...base, industry_id: "convenience_store", verdict_code: "clear", on_count: 0, basis: "proxy", signals: [
    signal({ key: "shrinking", level: "on", source: "neighborhood", evidence: "상권축소 근거" }),
    signal({ key: "tobacco_gap", level: "strong", source: "tobacco", evidence: "담배권 근거" }),
  ] }} />);
  expect(screen.getByText("참고: 상권축소 근거")).toBeInTheDocument();
  expect(screen.getByText("참고: 담배권 근거")).toBeInTheDocument();
  expect(screen.getByText("담배소매인 이력 기준")).toBeInTheDocument();
});
