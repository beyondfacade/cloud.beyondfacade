import { describe, expect, it } from "vitest";
import { METRICS, SNAPSHOT_INDUSTRIES, YEARS, DEFAULT_STATE } from "./map-state";
import { QUARTERS } from "./quarters";
import {
  SNAPSHOT_METRIC,
  SNAPSHOT_YEAR,
  availableQuarters,
  availableYears,
  clampToCoverage,
  isMetricMissingForIndustry,
} from "./metric-coverage";

describe("지표별 데이터 보유 범위", () => {
  it("일반 업종은 전 연도를 고를 수 있다", () => {
    expect(availableYears("closure_rate", "cafe")).toEqual(YEARS);
    expect(availableYears("store_count", "hair_salon")).toEqual(YEARS);
  });

  it("스냅샷 업종의 점포수는 관측 연도 하나뿐이다", () => {
    // 어린이집·편의점은 개폐업 이력이 없어 최신 관측 연도에만 적재된다 (실측: 2026년만 426·427행)
    for (const industry of SNAPSHOT_INDUSTRIES) {
      expect(availableYears(SNAPSHOT_METRIC, industry)).toEqual([SNAPSHOT_YEAR]);
    }
  });

  it("스냅샷 업종의 폐업률·성장률은 연도를 좁히지 않는다", () => {
    // 어느 연도에도 없으므로 연도를 걸러내면 원인(지표)이 가려진다 — 안내 문구가 설명할 몫이다
    expect(availableYears("closure_rate", "childcare")).toEqual(YEARS);
    expect(isMetricMissingForIndustry("closure_rate", "childcare")).toBe(true);
    expect(isMetricMissingForIndustry("store_count", "childcare")).toBe(false);
    expect(isMetricMissingForIndustry("closure_rate", "cafe")).toBe(false);
  });

  it("학원은 점포수는 전 연도지만 폐업률·성장률은 없다", () => {
    // 서울 학원 API는 폐원일자를 주지 않는다 — 백엔드 v0.35.3부터 0.0이 아니라 NULL (STATUS §4-3)
    expect(availableYears("store_count", "academy")).toEqual(YEARS);
    expect(isMetricMissingForIndustry("store_count", "academy")).toBe(false);
    expect(isMetricMissingForIndustry("closure_rate", "academy")).toBe(true);
    expect(isMetricMissingForIndustry("growth_rate", "academy")).toBe(true);
  });

  it("동네 지표는 업종과 무관하게 전 연도·전 분기다", () => {
    // 2026-09-24 실측: 동네 지표 4종 모두 22분기 × 422행, 공백 없음
    for (const metric of ["neighborhood_type", "night_index", "fnb_share", "operating_months"] as const) {
      expect(availableYears(metric, "childcare")).toEqual(YEARS);
      expect(availableQuarters(metric)).toEqual(QUARTERS);
    }
  });

  it("등록된 지표 전부가 커버리지 규칙을 통과한다", () => {
    // 지표를 늘리고 규칙을 안 더하면 여기서 걸린다
    for (const metric of METRICS) {
      expect(availableYears(metric, "cafe").length).toBeGreaterThan(0);
      expect(availableQuarters(metric).length).toBeGreaterThan(0);
    }
  });
});

describe("범위 밖 시점 보정", () => {
  it("스냅샷 업종·점포수에서 옛 연도를 고르면 관측 연도로 당긴다", () => {
    const out = clampToCoverage({ ...DEFAULT_STATE, metric: "store_count", industry: "childcare", year: 2020 });
    expect(out.year).toBe(SNAPSHOT_YEAR);
  });

  it("유효한 값은 그대로 둔다 (멱등)", () => {
    const valid = { ...DEFAULT_STATE, metric: "store_count" as const, industry: "cafe", year: 2023 };
    expect(clampToCoverage(valid)).toEqual(valid);
    expect(clampToCoverage(clampToCoverage(valid))).toEqual(valid);
  });

  it("보정은 연도만 건드린다", () => {
    const before = { ...DEFAULT_STATE, metric: "store_count" as const, industry: "childcare", year: 2019, region: "1168064000" };
    const after = clampToCoverage(before);
    expect(after).toEqual({ ...before, year: SNAPSHOT_YEAR });
  });
});
