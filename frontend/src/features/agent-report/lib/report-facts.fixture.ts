import type { EventAnalogs, IndustryMove, ReportFacts } from "@/shared/api/types";

function move(industry_id: string, industry_name: string, excess_pct: number | null): IndustryMove {
  return { industry_id, industry_name, openings: 100, closings: 80, openings_yoy_pct: 1, closings_yoy_pct: 2, stock_change_pct: 0.5, excess_pct };
}

/** 유사 사례 표본 — 진행 중 1건 + 지난 사례 1건. */
export function eventAnalogs(): EventAnalogs {
  return {
    industry_id: "cafe", months: 3, years: 1, as_of: "2026-08",
    categories: [
      { category: "pandemic", label: "감염병·방역", reason: "question" },
      { category: "minimum_wage", label: "최저임금", reason: "current" },
    ],
    current_events: [{
      event_id: "min-wage-2026", name: "최저임금 인상 — 2026년", category: "minimum_wage", category_label: "최저임금",
      start_date: "2026-01-01", end_date: "2026-12-31", duration_months: 11, description: null, source: "고용노동부", current: true,
      windows: [{ kind: "immediate", label: "직후 3개월", start_month: "2026-01", end_month: "2026-03", target: move("cafe", "카페", 0.6), strongest: [move("pc_bang", "PC방", 0.9)], weakest: [move("gym", "헬스장", -1.3)] }],
    }],
    analogs: [{
      event_id: "outbreak-covid19-20200120", name: "코로나19 국내 유행과 방역 조치", category: "pandemic", category_label: "감염병·방역",
      start_date: "2020-01-20", end_date: "2022-04-17", duration_months: 27, description: null, source: "보건복지부", current: false,
      windows: [
        { kind: "immediate", label: "직후 3개월", start_month: "2020-01", end_month: "2020-03", target: move("cafe", "카페", -0.8),
          strongest: [move("chinese_food", "중식", 0.8), move("pub", "호프·주점", 0.7)], weakest: [move("cafe", "카페", -0.8), move("pc_bang", "PC방", -0.6)] },
        { kind: "late", label: "1년 차 마지막 3개월", start_month: "2020-10", end_month: "2020-12", target: move("cafe", "카페", -1.4),
          strongest: [move("gym", "헬스장", 0.9)], weakest: [move("billiard", "당구장", -9.1)] },
      ],
    }],
    outlooks: [{
      category: "pandemic", label: "감염병·방역", analog_count: 2, target_trend: "weak",
      recommended: [{ industry_id: "western_food", industry_name: "양식" }, { industry_id: "chinese_food", industry_name: "중식" }],
      avoid: [{ industry_id: "pc_bang", industry_name: "PC방" }],
      typical_duration_months: 17,
    }],
    caveats: ["12월에는 행정 정리로 폐업이 몰린다 — 10~12월이 걸린 창은 변동폭이 크게 나올 수 있다."],
  };
}

/** 리포트 컴포넌트 테스트 전용 사실 표본. */
export function reportFacts(): ReportFacts {
  return {
    region: { code: "1168064000", name: "역삼1동", industry_id: "cafe", industry_name: "카페" },
    verdict: {
      basis: "permit",
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
    analogs: eventAnalogs(),
    funding_candidates: [{ program_id: "p1", title: "창업 지원", org: "서울시", why: "창업에 맞는 지원사업", summary: "사업비 지원", field_category: "창업", apply_period: "상시", url: "https://example.com/funding" }],
    budget: null,
  };
}
