import { describe, expect, it } from "vitest";
import { METRICS, METRIC_GROUPS, metricGroupOf } from "./map-state";
import { METRIC_SOURCES, type MetricQuery } from "./metric-sources";

const Q: MetricQuery = { industry: "cafe", year: 2026, yearQuarter: null };

describe("지표 원천 레지스트리", () => {
  it("선택 가능한 지표 전부에 원천이 등록돼 있다", () => {
    // 등록을 빠뜨리면 그 지표를 고르는 순간 화면이 터진다
    for (const metric of METRICS) {
      expect(METRIC_SOURCES[metric]).toBeDefined();
    }
  });

  it("무리의 축과 원천의 축이 같다 — 어긋나면 셀렉터가 거짓말한다", () => {
    for (const group of METRIC_GROUPS) {
      for (const metric of group.metrics) {
        expect(METRIC_SOURCES[metric].axis, metric).toBe(group.axis);
      }
    }
  });

  it("업종 지표의 질의 키는 업종·연도를 포함하고 분기를 포함하지 않는다", () => {
    expect(METRIC_SOURCES.closure_rate.queryKey({ ...Q, yearQuarter: "20254" })).toEqual([
      "metrics",
      "closure_rate",
      "cafe",
      2026,
    ]);
  });

  it("동 단위 지표의 질의 키는 업종·연도를 포함하지 않고 분기를 포함한다", () => {
    // 업종·연도를 넣으면 같은 응답을 업종 10종 × 연도 8개만큼 중복 캐싱한다
    const key = METRIC_SOURCES.operating_months.queryKey(Q);
    expect(key).toEqual(["commerce-change-metrics", "operating_months", null]);
    expect(METRIC_SOURCES.operating_months.queryKey({ industry: "karaoke", year: 2019, yearQuarter: null })).toEqual(key);
    expect(METRIC_SOURCES.night_index.queryKey({ ...Q, yearQuarter: "20254" })).toEqual(["profile-metrics", "night_index", "20254"]);
    expect(METRIC_SOURCES.neighborhood_type.queryKey({ ...Q, yearQuarter: "20254" })).toEqual(["profile-types", "20254"]);
  });

  it("유형은 범주 원천이고 나머지는 숫자 원천이다 — kind가 스케일·범례를 가른다", () => {
    expect(METRIC_SOURCES.neighborhood_type.kind).toBe("categorical");
    for (const metric of ["closure_rate", "growth_rate", "store_count", "operating_months", "night_index", "fnb_share"] as const) {
      expect(METRIC_SOURCES[metric].kind).toBe("numeric");
    }
  });

  it("숫자 원천은 색 스킴을 함께 선언한다 — 성장률만 발산형", () => {
    const scheme = (m: "closure_rate" | "growth_rate" | "store_count" | "operating_months" | "night_index" | "fnb_share") => {
      const source = METRIC_SOURCES[m];
      return source.kind === "numeric" ? source.scheme : null;
    };
    expect(scheme("growth_rate")).toBe("diverging");
    for (const m of ["closure_rate", "operating_months", "night_index", "fnb_share"] as const) {
      expect(scheme(m)).toBe("sequential");
    }
  });
});

it("모든 지표가 원천을 갖고, 원천의 축은 무리의 축과 같다", () => {
  for (const metric of METRICS) {
    expect(METRIC_SOURCES[metric].axis, metric).toBe(metricGroupOf(metric).axis);
  }
  expect(METRIC_GROUPS.map((g) => g.axis)).toEqual(["region_quarter", "industry_year", "industry_latest"]);
});

it("범주 원천은 팔레트·순서·라벨을 스스로 안다 — 지도·범례가 동네 유형을 하드코딩하지 않는다", () => {
  for (const metric of ["neighborhood_type", "verdict"] as const) {
    const source = METRIC_SOURCES[metric];
    if (source.kind !== "categorical") throw new Error(`${metric}는 범주 원천이어야 한다`);
    expect(source.order.length).toBeGreaterThan(0);
    for (const code of source.order) {
      expect(source.palette("light")[code], `${metric}/${code} light`).toMatch(/^#/);
      expect(source.palette("dark")[code], `${metric}/${code} dark`).toMatch(/^#/);
      expect(source.labelOf(code).name.length).toBeGreaterThan(0);
    }
  }
  const verdict = METRIC_SOURCES.verdict;
  if (verdict.kind !== "categorical") throw new Error();
  expect(verdict.order).toEqual(["red", "orange", "clear", "insufficient"]);
  expect(verdict.queryKey({ industry: "korean_food", year: 2026, yearQuarter: null })).toEqual(["verdicts", "korean_food"]);
});
