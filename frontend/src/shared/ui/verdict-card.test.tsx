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

it("판정 근거 약함 배지는 weak_basis가 true일 때만 표시한다", () => {
  const verdict = { ...base, industry_id: "japanese_food", basis: "permit" as const, signals: [], weak_basis: true };
  const { rerender } = render(<VerdictCard industryLabel="일식" verdict={verdict} />);
  expect(screen.getByText("판정 근거 약함")).toHaveAttribute("title", "이 업종은 과거 여러 시점에서 경고 신호가 폐업을 꾸준히 가르지 못했습니다. 신호가 켜져도 비추천은 내지 않습니다.");
  rerender(<VerdictCard industryLabel="일식" verdict={{ ...verdict, weak_basis: false }} />);
  expect(screen.queryByText("판정 근거 약함")).toBeNull();
});

it("켜진 신호에 위험 등급 라벨이 있으면 카드에 표시한다", () => {
  render(<VerdictCard industryLabel="부동산중개업" verdict={{ ...base, basis: "permit", signals: [signal({ level: "on", band: "bad", band_label: "높은 편" })] }} />);
  expect(screen.getByText("높은 편")).toBeVisible();
});

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

it("담배권 빈자리가 켜지면 참고 줄로 표시한다", () => {
  render(<VerdictCard industryLabel="편의점" verdict={{ ...base, industry_id: "convenience_store", verdict_code: "clear", on_count: 0, basis: "proxy", signals: [
    signal({ key: "tobacco_gap", level: "strong", source: "tobacco", evidence: "담배권 근거" }),
  ] }} />);
  expect(screen.getByText("참고: 담배권 근거")).toBeInTheDocument();
  expect(screen.getByText("담배소매인 이력 기준")).toBeInTheDocument();
});
