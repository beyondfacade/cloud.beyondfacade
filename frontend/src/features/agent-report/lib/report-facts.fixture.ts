import type { ReportFacts } from "@/shared/api/types";

/** 리포트 컴포넌트 테스트 전용 사실 표본. */
export function reportFacts(): ReportFacts {
  return {
    region: { code: "1168064000", name: "역삼1동", industry_id: "cafe", industry_name: "카페" },
    verdict: {
      region_code: "1168064000", industry_id: "cafe", verdict_code: "orange", strong_count: 1, on_count: 2,
      computed_at: "2026-09-29T04:30:00+09:00",
      signals: [
        { key: "net_outflow", level: "strong", percentile: 95, value: 0.2, source: "store", evidence: "순유출 근거" },
        { key: "survival_cliff", level: "on", percentile: 80, value: 0.1, source: "store", evidence: "생존 근거" },
        { key: "early_closure", level: "off", percentile: 20, value: 0.1, source: "store", evidence: "폐업 근거" },
        { key: "saturation", level: "unavailable", percentile: null, value: null, source: "metric", evidence: "자료 부족" },
        { key: "shrinking", level: "on", percentile: null, value: 1, source: "neighborhood", evidence: "축소 근거" },
      ],
    },
    alternatives: {
      region_code: "1168064000", industry_id: "cafe", neighborhood_type: "office",
      industries: [{ industry_id: "snack", industry_name: "분식", verdict_code: "clear", on_count: 0, strong_count: 0 }],
      regions: [{ region_code: "1168065000", region_name: "역삼2동", verdict_code: "orange", on_count: 1, strong_count: 0 }],
    },
    profile: {
      region_code: "1168064000", year_quarter: "20262", neighborhood_type: "office", type_reason: "직장인구 우위",
      time_label: "day", peak_block: "day", trough_block: "night", worker_resident_ratio: 5.9,
      weekend_index: 0.7, night_index: 0.64, footfall_20s_share: 0.22, fnb_share: 0.016, facility_total: 542,
      resident_total: 34082, block_intensities: { morning: 0.9, day: 1.4, evening: 1.1, night: 0.6 },
    },
    hour_gap: { region_code: "1168064000", industry_id: "cafe", year_quarter: "20254", bands: [
      { hour_band: "11_14", footfall_intensity: 1.4, sales_intensity: 2.9, gap: 1.5 },
      { hour_band: "14_17", footfall_intensity: 1.5, sales_intensity: 1.6, gap: 0.1 },
    ] },
    commerce_change: { region_code: "1168064000", year_quarter: "20262", change_code: "HL", change_name: "상권축소", operating_months: 110, closed_months: 48, seoul: { operating_months: 118, closed_months: 54 } },
    metrics_history: [
      { year: 2025, store_count: 100, open_count: 10, close_count: 5, closure_rate: 0.05, growth_rate: -0.02 },
      { year: 2026, store_count: 120, open_count: 25, close_count: 5, closure_rate: 0.04, growth_rate: 0.2 },
    ],
    population: { available: false, reason: "인구 자료가 없습니다." },
    shocks: [{ event_id: "s1", name: "원두 가격 상승", start_date: "2026-09-01", industry_specific: true }], news: [],
    funding_candidates: [{ program_id: "p1", title: "창업 지원", org: "서울시", why: "창업에 맞는 지원사업", summary: "사업비 지원", field_category: "창업", apply_period: "상시", target: "창업", url: "https://example.com/funding" }],
    budget: null,
  };
}
