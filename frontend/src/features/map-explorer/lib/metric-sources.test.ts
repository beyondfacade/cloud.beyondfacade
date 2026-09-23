import { describe, expect, it } from "vitest";
import { METRICS } from "./map-state";
import { METRIC_SOURCES } from "./metric-sources";

describe("지표 원천 레지스트리", () => {
  it("선택 가능한 지표 전부에 원천이 등록돼 있다", () => {
    // 등록을 빠뜨리면 그 지표를 고르는 순간 화면이 터진다
    for (const metric of METRICS) {
      expect(METRIC_SOURCES[metric]).toBeDefined();
    }
  });

  it("업종 지표의 질의 키는 업종·연도를 포함한다", () => {
    expect(METRIC_SOURCES.closure_rate.queryKey("cafe", 2026)).toEqual([
      "metrics",
      "closure_rate",
      "cafe",
      2026,
    ]);
  });

  it("동 단위 지표의 질의 키는 업종·연도를 포함하지 않는다", () => {
    // 넣으면 같은 응답을 업종 10종 × 연도 8개만큼 중복 캐싱한다
    const key = METRIC_SOURCES.operating_months.queryKey("cafe", 2026);

    expect(key).toEqual(["commerce-change-metrics", "operating_months"]);
    expect(METRIC_SOURCES.operating_months.queryKey("karaoke", 2019)).toEqual(key);
  });

  it("유형은 범주 원천이고 나머지는 숫자 원천이다 — kind가 스케일·범례를 가른다", () => {
    expect(METRIC_SOURCES.neighborhood_type.kind).toBe("categorical");
    for (const metric of ["closure_rate", "growth_rate", "store_count", "operating_months"] as const) {
      expect(METRIC_SOURCES[metric].kind).toBe("numeric");
    }
  });

  it("유형의 질의 키도 업종·연도를 포함하지 않는다", () => {
    expect(METRIC_SOURCES.neighborhood_type.queryKey("cafe", 2026)).toEqual(["profile-types"]);
  });

  it("숫자 원천은 색 스킴을 함께 선언한다 — 성장률만 발산형", () => {
    const scheme = (m: "closure_rate" | "growth_rate" | "store_count" | "operating_months") => {
      const source = METRIC_SOURCES[m];
      return source.kind === "numeric" ? source.scheme : null;
    };
    expect(scheme("growth_rate")).toBe("diverging");
    expect(scheme("closure_rate")).toBe("sequential");
    expect(scheme("operating_months")).toBe("sequential");
  });
});
