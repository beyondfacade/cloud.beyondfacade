import type { AnalogQuarter, EventAnalogs, ReportFacts } from "@/shared/api/types";

/** 이벤트 달부터 3개월씩 count개 분기. overlaps는 분기 번호(1부터) → 겹친 이벤트 이름. */
export function analogQuarters(year: number, month: number, count: number, overlaps: Record<number, string[]> = {}): AnalogQuarter[] {
  const ym = (offset: number) => {
    const index = year * 12 + month - 1 + offset;
    return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
  };
  return Array.from({ length: count }, (_, i) => ({
    quarter: i + 1, label: `${Math.floor(i / 4) + 1}년 차 ${(i % 4) + 1}분기`,
    start_month: ym(i * 3), end_month: ym(i * 3 + 2), overlaps: overlaps[i + 1] ?? [],
  }));
}

/** 유사 사례 표본 — 진행 중 1건(2분기) + 지난 사례 1건(12분기). */
export function eventAnalogs(): EventAnalogs {
  return {
    industry_id: "cafe", as_of: "2026-08",
    categories: [
      { category: "pandemic", label: "감염병·방역", reason: "question" },
      { category: "minimum_wage", label: "최저임금", reason: "current" },
    ],
    current_events: [{
      event_id: "min-wage-2026", name: "최저임금 인상 — 2026년", category: "minimum_wage", category_label: "최저임금",
      start_date: "2026-01-01", end_date: "2026-12-31", duration_months: 11, description: null, source: "고용노동부", current: true, years: 1,
      quarters: analogQuarters(2026, 1, 2),
      series: [{ industry_id: "cafe", industry_name: "카페", role: "target", values: [0.6, 0.5] }],
      target_weak_quarters: 0, target_strong_quarters: 2, target_weak_streak: 0,
    }],
    analogs: [{
      event_id: "outbreak-covid19-20200120", name: "코로나19 국내 유행과 방역 조치", category: "pandemic", category_label: "감염병·방역",
      start_date: "2020-01-20", end_date: "2022-04-17", duration_months: 27, description: null, source: "보건복지부", current: false, years: 3,
      quarters: analogQuarters(2020, 1, 12, { 2: ["1차 긴급재난지원금 지급"], 8: ["소상공인 손실보상제 시행"] }),
      series: [
        { industry_id: "cafe", industry_name: "카페", role: "target", values: [-0.8, -1.1, -0.6, -1.4, -0.7, -1.4, -0.9, -0.4, -1.2, -1.6, -1.2, -1.7] },
        { industry_id: "western_food", industry_name: "양식", role: "recommended", values: [0.6, 0.6, 1.2, 0.4, 2.5, 0.9, 1.2, -0.2, 1.1, 0.4, 0.5, null] },
        { industry_id: "pc_bang", industry_name: "PC방", role: "avoid", values: [-0.6, -1.2, -1.7, -1.5, -2.4, 0.4, 0.4, -1.1, -6.5, 0.1, 0.0, -1.0] },
      ],
      target_weak_quarters: 12, target_strong_quarters: 0, target_weak_streak: 12,
    }],
    outlooks: [{
      category: "pandemic", label: "감염병·방역", analog_count: 2, target_trend: "weak",
      recommended: [{ industry_id: "western_food", industry_name: "양식" }, { industry_id: "chinese_food", industry_name: "중식" }],
      avoid: [{ industry_id: "pc_bang", industry_name: "PC방" }],
      typical_duration_months: 17,
    }],
    caveats: ["12월에는 행정 정리로 폐업이 몰린다 — 12월이 든 분기는 한 번씩 크게 튈 수 있어 판단은 분기 과반으로 한다."],
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
