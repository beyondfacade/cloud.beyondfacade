import { readFileSync } from "node:fs";
import path from "node:path";
import type { FeatureCollection, MultiPolygon } from "geojson";
import type {
  AgentEvent,
  AnalogQuarter,
  EventAnalogs,
  ReportFacts,
  ReportSection,
  ChildcareCenter,
  FinancePrefill,
  FundingCandidate,
  SupportGuide,
  SupportItem,
  PlanQuestion,
  ConvenienceRegionSummary,
  IntentCandidate,
  IntentDiagnosis,
  IntentResult,
  ConvenienceStore,
  MetricKey,
  MetricRow,
  RegionCommerceChangeDetail,
  RegionIndustryHourGap,
  RegionIndustryVerdict,
  VerdictAlternatives,
  RegionProfile,
  RegionSummary,
  Store,
  SummaryCard,
  VerdictCode,
  VerdictBasis,
  VerdictRow,
  VerdictSignal,
  VerdictBand,
  VerdictSignalKey,
  VerdictSignalSource,
} from "@/shared/api/types";
import { STORE_SAMPLES, type StoreSample } from "./store-samples";
import { INDUSTRIES, INDUSTRY_LABELS, type IndustryId } from "@/shared/industries";
import { ADVISORY_SIGNAL_KEYS, isVerdictIndustry, verdictLabel } from "@/shared/verdict";
import { neighborhoodTypeLabel } from "@/shared/neighborhood";
import { SEOUL_DISTRICTS, districtOf } from "@/shared/seoul-districts";

type RegionProperties = { region_code: string; name: string };

/** 서울 행정동 427개 실경계 — vuski/admdongkor ver20260701 원천, 백엔드 GET /regions/geojson 산출물 스냅샷 (BE v0.84.0, 좌표 5자리 절삭).
 *  서버 전용 모듈(mock 라우트·테스트)에서만 import — 클라이언트 번들에 실리지 않는다. */
export const SEOUL_REGIONS_GEOJSON: FeatureCollection<MultiPolygon, RegionProperties> = JSON.parse(
  readFileSync(path.join(process.cwd(), "public", "geojson", "seoul-regions.geojson"), "utf-8"),
);

const REGIONS: RegionProperties[] = SEOUL_REGIONS_GEOJSON.features.map((f) => f.properties);

/** 문자열 시드 → 결정적 정수 해시 (FNV-1a). Math.random 사용 금지 — 테스트 재현성. */
function hashSeed(...parts: (string | number)[]): number {
  const str = parts.join("|");
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

function unitFrom(seed: number): number {
  return (seed % 10000) / 10000; // [0, 1)
}

const METRIC_RANGES: Record<MetricKey, [number, number]> = {
  closure_rate: [0.02, 0.18],
  growth_rate: [-0.08, 0.12],
  store_count: [15, 320],
};

export function metricRows(metric: MetricKey, year: number, industry: string): MetricRow[] {
  // 실 API는 스냅샷 업종(어린이집·편의점)에 관측 연도의 점포수만 준다 — 나머지 조합은 빈 배열이다.
  // mock이 늘 427행을 주면 mock으로 개발하는 동안 "빈 지도" 경로를 한 번도 못 본다 (§15 미러 규칙).
  // 지표 자체가 없는 경우(폐업률·성장률)와 연도가 없는 경우를 둘 다 막는다.
  const snapshot = industry === "childcare" || industry === "convenience_store";
  if ((snapshot || industry === "academy") && metric !== "store_count") return [];
  if (snapshot ? year !== 2026 : year < 2019 || year > 2026 || !Number.isInteger(year)) return [];
  const [min, max] = METRIC_RANGES[metric];
  return REGIONS.map(({ region_code }) => {
    const u = unitFrom(hashSeed(metric, year, industry, region_code));
    const raw = min + u * (max - min);
    const value = metric === "store_count" ? Math.round(raw) : Math.round(raw * 1000) / 1000;
    return { region_code, value };
  });
}

export function summaryOf(code: string, industry: string): RegionSummary {
  const name = REGIONS.find((r) => r.region_code === code)?.name ?? "알 수 없음";
  const storeCount = metricRows("store_count", 2026, industry).find((r) => r.region_code === code)?.value ?? 0;
  const closureRate = metricRows("closure_rate", 2026, industry).find((r) => r.region_code === code)?.value ?? 0;
  const growthRate = metricRows("growth_rate", 2026, industry).find((r) => r.region_code === code)?.value ?? 0;
  const newsSeed = unitFrom(hashSeed("news", code, industry));

  const cards: SummaryCard[] = [
    { label: "점포수", value: `${storeCount}개`, grade: "fact" },
    { label: "폐업률", value: `${(closureRate * 100).toFixed(1)}%`, grade: "fact" },
    { label: "성장률", value: `${growthRate >= 0 ? "+" : ""}${(growthRate * 100).toFixed(1)}%`, grade: "fact" },
    {
      label: "뉴스 신호",
      value: newsSeed > 0.5 ? "최근 30일 신규 카페 오픈 소식 증가" : "임대료 상승 관련 언급 감지",
      grade: "signal",
    },
    {
      label: "상권 활력",
      value: newsSeed > 0.3 ? "유동인구 증가 추세 (SNS 언급 기반)" : "경쟁 점포 증가 신호",
      grade: "signal",
    },
  ];

  return { region_code: code, name, industry_id: industry, cards };
}

/** 영업 중으로 볼 수 있는 상태 — 그 외(폐업/취소류)는 status=closed 표본에 포함. */
const OPEN_STATUSES = new Set(["영업", "영업중"]);

/** 결정적 폐업일 — 개업일 + (해시 % 36 + 3)개월. 표본에 폐업일 컬럼이 없어 여기서 만든다.
 *  실 API 계약(today − 2y ≤ close_date ≤ today)을 벗어나면 결정적으로 그 창 안으로 접는다. */
function closeDateOf(sample: StoreSample): string {
  const months = (hashSeed("close", sample.store_id) % 36) + 3;
  const d = new Date(sample.open_date);
  d.setMonth(d.getMonth() + months);

  const today = new Date();
  const twoYearsAgo = new Date(today);
  twoYearsAgo.setDate(twoYearsAgo.getDate() - 730);
  const offsetDays = hashSeed("close", sample.store_id) % 700;

  if (d.getTime() > today.getTime()) {
    const clamped = new Date(today);
    clamped.setDate(clamped.getDate() - offsetDays);
    return clamped.toISOString().slice(0, 10);
  }
  if (d.getTime() < twoYearsAgo.getTime()) {
    const clamped = new Date(twoYearsAgo);
    clamped.setDate(clamped.getDate() + offsetDays);
    return clamped.toISOString().slice(0, 10);
  }
  return d.toISOString().slice(0, 10);
}

/** region_code·industry_id로 STORE_SAMPLES를 필터링해 마커용 점포 목록을 반환한다.
 *  실적재 데이터가 없는 업종/동 조합은 빈 배열 — 이는 오류가 아니라 실데이터 부재를 그대로 반영한 것.
 *  status=closed는 표본 중 영업 상태가 아닌 것만, 결정적 close_date와 함께 준다. */
export function storesOf(regionCode: string, industryId: string, status: "open" | "closed" = "open"): Store[] {
  const samples = (STORE_SAMPLES[regionCode] ?? []).filter((s) => s.industry_id === industryId);
  const picked = status === "closed" ? samples.filter((s) => !OPEN_STATUSES.has(s.status_name)) : samples;
  return picked.map(({ store_id, name, lat, lng, status_name, open_date }) => ({
    store_id,
    name,
    lat,
    lng,
    status_name,
    open_date,
    close_date: status === "closed" ? closeDateOf({ store_id, name, lat, lng, status_name, open_date, industry_id: industryId }) : null,
  }));
}

const CHILDCARE_TYPES = ["국공립", "가정", "민간", "직장"] as const;

/** 행정동 경계 bbox 중심 — 어린이집 픽스처 좌표를 동 안쪽에 두기 위한 근사. */
function regionCenter(regionCode: string): [number, number] | null {
  const feature = SEOUL_REGIONS_GEOJSON.features.find((f) => f.properties.region_code === regionCode);
  if (!feature) return null;
  const points = feature.geometry.coordinates.flat(2);
  const lngs = points.map(([lng]) => lng);
  const lats = points.map(([, lat]) => lat);
  return [(Math.min(...lngs) + Math.max(...lngs)) / 2, (Math.min(...lats) + Math.max(...lats)) / 2];
}

/** 행정동별 결정적 어린이집 1~6곳 — 실데이터 분포(정원 20~120, 가동률 40~100%, 대기 공란 흔함)를 흉내 낸다. */
export function childcareCentersOf(regionCode: string): ChildcareCenter[] {
  const center = regionCenter(regionCode);
  if (!center) return [];
  const count = 1 + (hashSeed("childcare-count", regionCode) % 6);
  return Array.from({ length: count }, (_, i) => {
    const seed = hashSeed("childcare", regionCode, i);
    const capacity = 20 + (seed % 101);
    const occupancy = 0.4 + unitFrom(hashSeed("occupancy", regionCode, i)) * 0.6;
    const type = CHILDCARE_TYPES[seed % CHILDCARE_TYPES.length];
    return {
      center_id: `${regionCode.slice(0, 5)}${String(i + 1).padStart(6, "0")}`,
      name: `${type === "국공립" ? "구립" : ""}시험${i + 1}어린이집`,
      type_name: type,
      status_name: "정상",
      lat: center[1] + (unitFrom(hashSeed("lat", regionCode, i)) - 0.5) * 0.004,
      lng: center[0] + (unitFrom(hashSeed("lng", regionCode, i)) - 0.5) * 0.004,
      base_date: "2026-09-17",
      capacity,
      child_count: Math.round(capacity * occupancy),
      waiting_count: seed % 4 === 0 ? null : seed % 61,
    };
  });
}

const CONVENIENCE_BRANDS = ["GS25", "CU", "세븐일레븐", "이마트24", "미니스톱", null] as const;

/** 행정동별 결정적 편의점 2~15곳 — 브랜드 미확인(null) 포함. */
export function convenienceStoresOf(regionCode: string): ConvenienceStore[] {
  const center = regionCenter(regionCode);
  if (!center) return [];
  const count = 2 + (hashSeed("convenience-count", regionCode) % 14);
  return Array.from({ length: count }, (_, i) => {
    const seed = hashSeed("convenience", regionCode, i);
    const brand = CONVENIENCE_BRANDS[seed % CONVENIENCE_BRANDS.length];
    return {
      store_id: `MA${regionCode}${String(i + 1).padStart(4, "0")}`,
      name: `${brand ?? "동네"}시험${i + 1}점`,
      branch_name: null,
      brand,
      lat: center[1] + (unitFrom(hashSeed("cv-lat", regionCode, i)) - 0.5) * 0.004,
      lng: center[0] + (unitFrom(hashSeed("cv-lng", regionCode, i)) - 0.5) * 0.004,
      road_address: null,
    };
  });
}

/** convenienceStoresOf 브랜드 집계 — 실 API ConvenienceRegionSummary.of 정렬 규칙과 동일
 *  (건수 내림차순·동수는 브랜드명 순, 미확인 null은 맨 뒤). */
export function convenienceSummaryOf(regionCode: string): ConvenienceRegionSummary {
  const stores = convenienceStoresOf(regionCode);
  const counts = new Map<string | null, number>();
  for (const store of stores) counts.set(store.brand, (counts.get(store.brand) ?? 0) + 1);
  const known = [...counts]
    .filter((entry): entry is [string, number] => entry[0] !== null)
    .map(([brand, count]) => ({ brand, count }))
    .sort((a, b) => b.count - a.count || a.brand.localeCompare(b.brand));
  const unknown = counts.has(null) ? [{ brand: null, count: counts.get(null)! }] : [];
  return {
    region_code: regionCode,
    store_count: stores.length,
    brands: [...known, ...unknown],
    source_stdr_ym: stores.length > 0 ? "202606" : null,
  };
}

/** 고정 시연 입력의 사실 선수집 → 문장 스트리밍. 실 API의 이벤트 순서·스키마를 미러한다. */
/** 이벤트 달부터 3개월씩 count개 분기 — 라벨·달은 리포트 facts의 유사 사례 계약과 같다. */
function demoQuarters(year: number, month: number, count: number, overlaps: Record<number, string[]> = {}): AnalogQuarter[] {
  const ym = (offset: number) => {
    const index = year * 12 + month - 1 + offset;
    return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
  };
  return Array.from({ length: count }, (_, i) => ({
    quarter: i + 1, label: `${Math.floor(i / 4) + 1}년 차 ${(i % 4) + 1}분기`,
    start_month: ym(i * 3), end_month: ym(i * 3 + 2), overlaps: overlaps[i + 1] ?? [],
  }));
}

/** 유사 사례 시연 표본 — 분기·업종 흐름 구조는 리포트 facts의 유사 사례 계약과 같다. 수치는 시연용이다. */
function eventAnalogsDemo(industryId: string, industryName: string): EventAnalogs {
  return {
    industry_id: industryId, as_of: "2026-08",
    categories: [
      { category: "pandemic", label: "감염병·방역", reason: "question" },
      { category: "minimum_wage", label: "최저임금", reason: "current" },
    ],
    current_events: [{
      event_id: "min-wage-2026", name: "최저임금 인상 — 2026년 시급 10,320원(+2.9%)", category: "minimum_wage", category_label: "최저임금",
      start_date: "2026-01-01", end_date: "2026-12-31", duration_months: 11, description: null, source: "고용노동부 최저임금 고시", current: true, years: 1,
      quarters: demoQuarters(2026, 1, 2),
      series: [
        { industry_id: industryId, industry_name: industryName, role: "target", values: [0.6, 0.5] },
        { industry_id: "pc_bang", industry_name: "PC방", role: "recommended", values: [0.9, 0.0] },
        { industry_id: "gym", industry_name: "헬스장", role: "avoid", values: [-1.3, -1.5] },
      ],
      target_weak_quarters: 0, target_strong_quarters: 2, target_weak_streak: 0,
    }],
    analogs: [{
      event_id: "outbreak-covid19-20200120", name: "코로나19 국내 유행과 방역 조치", category: "pandemic", category_label: "감염병·방역",
      start_date: "2020-01-20", end_date: "2022-04-17", duration_months: 27, description: null, source: "보건복지부·중앙재난안전대책본부 보도자료", current: false, years: 3,
      quarters: demoQuarters(2020, 1, 12, {
        1: ["최저임금 인상 — 2020년", "주 52시간제 시행 — 50~299인 사업장"], 2: ["1차 긴급재난지원금 지급 (전 국민)"],
        5: ["최저임금 인상 — 2021년"], 8: ["소상공인 손실보상제 시행"], 9: ["최저임금 인상 — 2022년"],
      }),
      series: [
        { industry_id: industryId, industry_name: industryName, role: "target", values: [-0.8, -1.1, -0.6, -1.4, -0.7, -1.4, -0.9, -0.4, -1.2, -1.6, -1.2, -1.7] },
        { industry_id: "western_food", industry_name: "양식", role: "recommended", values: [0.6, 0.6, 1.2, 0.4, 2.5, 0.9, 1.2, -0.2, 1.1, 0.4, 0.5, -0.3] },
        { industry_id: "gym", industry_name: "헬스장", role: "recommended", values: [-0.6, -0.2, 1.3, 0.9, -4.5, 1.8, 1.2, 1.2, 2.2, 1.6, 1.4, 1.5] },
        { industry_id: "japanese_food", industry_name: "일식", role: "recommended", values: [-0.7, -0.9, 0.4, 0.8, 0.5, 1.7, 0.7, 0.8, 0.2, 0.6, 0.2, 0.6] },
        { industry_id: "pub", industry_name: "호프·주점", role: "avoid", values: [0.7, 0.6, -0.3, -0.8, 1.1, -1.3, -1.0, -0.9, 0.2, -0.3, -0.4, -1.1] },
        { industry_id: "korean_food", industry_name: "한식", role: "avoid", values: [0.6, 0.9, 0.2, -0.2, 0.8, -0.1, -0.5, -0.5, 0.6, 0.1, -0.5, -0.6] },
      ],
      target_weak_quarters: 12, target_strong_quarters: 0, target_weak_streak: 12,
    }],
    outlooks: [{
      category: "pandemic", label: "감염병·방역", analog_count: 1, target_trend: "weak",
      recommended: [
        { industry_id: "western_food", industry_name: "양식" }, { industry_id: "gym", industry_name: "헬스장" },
        { industry_id: "japanese_food", industry_name: "일식" },
      ],
      avoid: [{ industry_id: "pub", industry_name: "호프·주점" }, { industry_id: "korean_food", industry_name: "한식" }],
      typical_duration_months: 27,
      condition: {
        event_id: "outbreak-covid19-20200120", event_name: "코로나19 국내 유행과 방역 조치", direction: "weaker",
        before: { start_month: "2019-01", end_month: "2019-12", growth_pct: 7.1, all_growth_pct: 1.3, excess_pct: 5.8, closure_rate_pct: 14.0, rank: 1, industry_count: 12 },
        recent: { start_month: "2025-09", end_month: "2026-08", growth_pct: -1.1, all_growth_pct: -1.1, excess_pct: -0.1, closure_rate_pct: 20.1, rank: 6, industry_count: 12 },
      },
    }],
    caveats: [
      "12월에는 행정 정리로 폐업이 몰린다 — 12월이 든 분기는 한 번씩 크게 튈 수 있어 판단은 분기 과반으로 한다.",
      "2020~2022년 폐업은 재난지원금·손실보상으로 지연되어 실제보다 적게 잡혔을 수 있다.",
    ],
    hints: [
      { category: "work_hours", label: "근로시간", keyword: "52시간" },
      { category: "relief", label: "지원금·보상", keyword: "지원금" },
    ],
    recent_news: [{
      category: "pandemic", label: "감염병·방역", days: 30, keywords: ["집합금지", "영업제한", "거리두기 격상"],
      checked: true, article_count: 0, headlines: [],
    }],
  };
}

export function agentEventScript(hasQuestion = false): AgentEvent[] {
  const regionCode = "1168064000";
  const industryId = "cafe";
  const verdict = verdictOf(regionCode, industryId);
  const alternatives = alternativesOf(regionCode, industryId);
  const profile = regionProfileOf(regionCode, LATEST_PROFILE_QUARTER);
  const metricsHistory = Array.from({ length: 8 }, (_, index) => {
    const year = 2019 + index;
    const valueOf = (metric: MetricKey) => metricRows(metric, year, industryId).find((row) => row.region_code === regionCode)!.value;
    const storeCount = valueOf("store_count");
    const closureRate = valueOf("closure_rate");
    const growthRate = valueOf("growth_rate");
    // 개폐업 수는 기존 지표 픽스처에 없어 별도 결정적 시연 표본으로 둔다(실측 추정 아님).
    return {
      year, store_count: storeCount,
      open_count: 10 + hashSeed("open_count", year, regionCode, industryId) % 25,
      close_count: 5 + hashSeed("close_count", year, regionCode, industryId) % 20,
      closure_rate: closureRate, growth_rate: growthRate,
    };
  });
  const facts: ReportFacts = {
    region: { code: regionCode, name: REGIONS.find((r) => r.region_code === regionCode)!.name, industry_id: industryId, industry_name: INDUSTRY_LABELS[industryId] },
    verdict, alternatives, profile,
    hour_gap: hourGapOf(regionCode, industryId, LATEST_HOUR_GAP_QUARTER) ?? { available: false, reason: "시간대 자료가 없습니다." },
    commerce_change: commerceChangeDetailOf(regionCode, LATEST_PROFILE_QUARTER),
    metrics_history: metricsHistory,
    // 아직 별도 픽스처가 없는 도구 응답은 작은 결정적 표본으로 제공한다.
    population: { region_code: regionCode, resident_total: profile.resident_total },
    shocks: [{ event_id: "mock-shock-1", name: "원두 가격 상승", start_date: "2026-09-01", industry_specific: true, summary: "원가 변동에 따른 마진 영향을 확인하세요.", grade: "signal" }],
    analogs: eventAnalogsDemo(industryId, INDUSTRY_LABELS[industryId]),
    regional_events: [{
      start_date: "2026-09-15", end_date: null, name: "시연 대규모점포 개점",
      source: "서울 열린데이터광장 OA-16096 서울시 대규모점포 인허가 정보",
      source_url: "https://data.seoul.go.kr/dataList/OA-16096/S/1/datasetView.do",
    }],
    news: [],
    funding_candidates: fundingCandidatesOf(null).map((candidate) => ({
      program_id: candidate.program_id, title: candidate.title, org: candidate.org,
      why: candidate.why, summary: candidate.summary, url: candidate.url,
      field_category: candidate.field_category, apply_period: candidate.apply_period,
      deadline: candidate.deadline,
    })),
    budget: null,
  };
  const events: AgentEvent[] = [
    { type: "agent_status", agent: "orchestrator", status: "running" },
    { type: "agent_status", agent: "facts", status: "running" },
    { type: "facts", facts },
    { type: "agent_status", agent: "facts", status: "done" },
    { type: "agent_status", agent: "writer", status: "running" },
  ];
  if (hasQuestion) {
    events.push({
      type: "report_delta", section: "answer_lead",
      markdown: `[확인된 사실] ${facts.region.name} ${facts.region.industry_name} 창업은 ${verdictLabel(verdict.verdict_code).name} 판정입니다 — 켜진 경고 신호 ${verdict.on_count}개를 확인하세요.\n\n- [확인된 사실] 강한 경고 신호는 ${verdict.strong_count}개입니다.\n- [확인된 사실] 보증금·권리금·인테리어 비용 자료가 없어 예산이 충분한지는 판단할 수 없습니다 — 자금 계획 화면에서 계산하세요.`,
    });
  }
  const industryAlternatives = alternatives.industries.map((item) => `${item.industry_name}(${verdictLabel(item.verdict_code).name})`).join(", ") || "자료 없음";
  const regionAlternatives = alternatives.regions.map((item) => `${item.region_name}(${verdictLabel(item.verdict_code).name})`).join(", ") || "자료 없음";
  // 문장 경계에서 직접 나누어 소수점·마크다운·공백을 손상시키지 않는다.
  const sections: { section: ReportSection; sentences: string[] }[] = [
    { section: "verdict", sentences: [
      `### 판정\n\n**${verdictLabel(verdict.verdict_code).name}** 판정입니다. `,
      `켜진 신호 ${verdict.on_count}개와 강한 신호 ${verdict.strong_count}개를 확인하세요.`,
    ] },
    { section: "reasons", sentences: [
      "### 왜 안 되나\n\n점포 수와 폐업률의 연도별 변화를 함께 살펴보세요. ",
      "원두 원가 변동도 마진에 영향을 줄 수 있습니다.",
    ] },
    { section: "analogs", sentences: [
      "### 유사 사례\n\n코로나19 유행 뒤 3년 12분기 내내 카페는 평소보다 점포가 덜 늘었습니다. ",
      "비슷한 상황이 오면 약세가 길게 이어질 수 있으니, 지금은 카페 창업을 서두르기보다 양식·헬스장·일식처럼 사례에서 거듭 강세였던 업종을 먼저 검토하세요.",
    ] },
    { section: "conditions", sentences: [
      "### 그래도 한다면\n\n유동인구와 매출 시간대가 맞는지 확인하세요. ",
      "실제 임대료와 원가를 입력해 손익분기 매출을 검토하세요.",
    ] },
    { section: "alternatives", sentences: [
      `### 대안 동네·업종\n\n굳이 이 동네라면: ${industryAlternatives}.\n\n`,
      `굳이 카페라면: ${regionAlternatives}.`,
    ] },
    { section: "funding", sentences: [
      "### 대안 업종 지원사업\n\n후보 공고의 지원 대상과 대안 업종을 대조하세요. ",
      "신청 가능 여부는 업종과 사업자 요건 확인이 필요합니다.",
    ] },
  ];
  for (const { section, sentences } of sections) {
    for (const markdown of sentences) events.push({ type: "report_delta", section, markdown });
  }
  // 해석(answer)은 코드 6개 절 뒤에 한 번 — 숫자를 쓰지 않는 한 단락(실 API 계약과 같다)
  events.push({
    type: "report_delta", section: "answer",
    markdown: "판정 근거는 아래 신호와 폐업 추이에 있습니다. 손님이 몰리는 시간대에 맞춰 운영할 수 있는지 먼저 확인하세요. 같은 동네의 다른 업종과 같은 업종의 다른 동네도 함께 비교해 보세요.",
  });
  events.push(
    { type: "agent_status", agent: "writer", status: "done" },
    { type: "agent_status", agent: "orchestrator", status: "done" },
    {
      type: "report_done", report_id: "mock-report-001",
      citations: [
        { title: "강남 카페 상권 동향 (시연 자료)", url: "https://news.example.com/articles/mock-001", published_at: "2026-10-06", press: null, grade: "signal" },
      ],
    },
  );
  return events;
}

/** 동네 프로필 — 실 API의 6유형·5라벨·판정 근거 문장 형태를 그대로 흉내 낸다.
 *  분포는 실측(주거 60%·먹자 13%·낮인구 9%·혼합 8%·생활중심 6%·대학가 5%)에 맞춰 가중한다. */
const PROFILE_TYPE_WEIGHTS: [string, number][] = [
  ["residential", 60],
  ["dining", 13],
  ["office", 9],
  ["mixed", 8],
  ["hub", 6],
  ["campus", 4],
];

const PROFILE_TIME_LABELS = ["night", "flat", "day", "evening", "morning"] as const;
const PROFILE_BLOCKS = ["morning", "day", "evening", "night"] as const;

/** 유형별 정점→바닥 — 실측 교차(낮인구는 낮 88%, 주거는 밤 80%)를 반영한다. */
const PROFILE_PHASES: Record<string, [string, string]> = {
  office: ["day", "night"],
  campus: ["evening", "night"],
  dining: ["evening", "morning"],
  hub: ["day", "night"],
  residential: ["night", "day"],
  mixed: ["day", "night"],
};

function pickWeighted(seed: number): string {
  const total = PROFILE_TYPE_WEIGHTS.reduce((sum, [, w]) => sum + w, 0);
  let point = seed % total;
  for (const [code, weight] of PROFILE_TYPE_WEIGHTS) {
    if (point < weight) return code;
    point -= weight;
  }
  return "mixed";
}

function profileReason(type: string, ratio: number, share20s: number, fnbShare: number, facility: number): string {
  const reasons: Record<string, string> = {
    office: `직장인구가 상주인구의 ${ratio.toFixed(1)}배로 매우 높은 편(서울 동을 100곳으로 치면 높은 쪽 10곳 안)이고, 주말 유동이 평일보다 적습니다.`,
    campus: `대학 시설이 있고, 거리 위 20대 비중이 ${(share20s * 100).toFixed(1)}%로 매우 높은 편(서울 동을 100곳으로 치면 높은 쪽 10곳 안)입니다.`,
    dining: `결제액의 ${(fnbShare * 100).toFixed(1)}%가 음식·유흥으로 높은 편(서울 동을 100곳으로 치면 높은 쪽 25곳 안)이고, 밤 시간 체류가 낮은 편(서울 동을 100곳으로 치면 낮은 쪽 25곳 안)입니다.`,
    hub: `집객시설이 ${facility}개로 높은 편(서울 동을 100곳으로 치면 높은 쪽 25곳 안)이고, 낮 시간 유동이 밤보다 강합니다.`,
    residential: "직장인구가 상주인구보다 적고, 밤 시간 체류가 낮은 쪽이 아닙니다(서울 동을 100곳으로 치면 낮은 쪽 25곳 밖).",
    mixed: "어느 지표도 서울 동 가운데 두드러지게 높거나 낮지 않습니다.",
  };
  return reasons[type] ?? reasons.mixed;
}

export const LATEST_PROFILE_QUARTER = "20262";

export function regionProfileOf(regionCode: string, yearQuarter: string): RegionProfile {
  const seed = hashSeed("profile", regionCode, yearQuarter);
  const type = pickWeighted(seed);
  const unit = unitFrom(seed);
  const ratio = type === "office" ? 1.6 + unit * 6 : 0.03 + unit * 0.7;
  const share20s = type === "campus" ? 0.23 + unit * 0.25 : 0.08 + unit * 0.12;
  const fnbShare = type === "dining" ? 0.33 + unit * 0.3 : 0.12 + unit * 0.18;
  const facility = type === "hub" ? 155 + Math.floor(unit * 380) : 20 + Math.floor(unit * 130);
  const [peak, trough] = PROFILE_PHASES[type] ?? ["day", "night"];
  // 평탄도가 낮은 동은 정점이 있어도 라벨은 flat이다 (실 API와 같은 규칙)
  const isFlat = unit < 0.25;
  return {
    region_code: regionCode,
    year_quarter: yearQuarter,
    neighborhood_type: type,
    type_reason: profileReason(type, ratio, share20s, fnbShare, facility),
    time_label: isFlat ? "flat" : (PROFILE_BLOCKS.find((b) => b === peak) ?? PROFILE_TIME_LABELS[0]),
    peak_block: peak,
    trough_block: trough,
    // 직장인구 결측 11개 동을 흉내 낸다 — 화면이 null을 0으로 읽지 않는지 확인하는 자리
    worker_resident_ratio: unit < 0.03 ? null : Number(ratio.toFixed(3)),
    weekend_index: Number((type === "office" ? 0.7 + unit * 0.3 : 0.95 + unit * 0.2).toFixed(3)),
    night_index: Number((type === "office" ? 0.6 + unit * 0.35 : 0.95 + unit * 0.3).toFixed(3)),
    footfall_20s_share: Number(share20s.toFixed(4)),
    fnb_share: Number(fnbShare.toFixed(4)),
    facility_total: facility,
    resident_total: 3_000 + Math.floor(unit * 40_000),
    block_intensities: blockIntensitiesOf(peak, trough, unit),
  };
}

/** 4블록 강도 — 정점 1.4, 바닥 0.7, 나머지는 1 근처. 실 API처럼 배치가 준 값이라는 전제로 화면은 재계산하지 않는다. */
function blockIntensitiesOf(peak: string, trough: string, unit: number): RegionProfile["block_intensities"] {
  const blocks = { morning: 0, day: 0, evening: 0, night: 0 };
  for (const key of Object.keys(blocks) as (keyof typeof blocks)[]) {
    blocks[key] = key === peak ? 1.4 : key === trough ? 0.7 : Number((0.9 + unit * 0.2).toFixed(3));
  }
  return blocks;
}

// ---------------------------------------------------------------------------
// 관문 mock 파서 — 백엔드 apps/intent 규칙 경로의 미러. LLM 경로는 "홍대"→서교동 한 건만 흉내 낸다.
// ---------------------------------------------------------------------------

/** 번호·'제'·구분점을 지운 기본 이름 — 사람은 "역삼동"이라 말하고 마스터는 "역삼1동"이다 (백엔드 master_dictionary.base_name). */
function baseName(name: string): string {
  return name.replace(/[제\d.·]+/g, "");
}

const REGION_INDEX: Map<string, IntentCandidate[]> = (() => {
  const index = new Map<string, IntentCandidate[]>();
  for (const { region_code, name } of REGIONS) {
    const entry: IntentCandidate = {
      region_code, region_name: name, district_code: districtOf(region_code),
      district_name: SEOUL_DISTRICTS[districtOf(region_code)] ?? "",
    };
    for (const key of new Set([name, baseName(name)])) {
      const bucket = index.get(key) ?? [];
      bucket.push(entry);
      index.set(key, bucket);
    }
  }
  return index;
})();
const REGION_NAMES_LONGEST_FIRST = [...REGION_INDEX.keys()].sort((a, b) => b.length - a.length);
const DISTRICT_NAMES_LONGEST_FIRST = Object.entries(SEOUL_DISTRICTS).sort((a, b) => b[1].length - a[1].length);

const INDUSTRY_SYNONYMS: Record<string, IndustryId> = {
  카페: "cafe", 커피: "cafe", 디저트: "cafe", 편의점: "convenience_store", 미용실: "hair_salon", 헤어: "hair_salon",
  노래방: "karaoke", PC방: "pc_bang", 피시방: "pc_bang", 헬스장: "gym", 헬스: "gym", 당구장: "billiard",
  부동산: "real_estate", 공인중개: "real_estate", 학원: "academy", 교습소: "academy", 어린이집: "childcare",
  // 음식 6종 (2026-09-28, 백엔드 intent/industry_synonyms.py 미러) — restaurant_other는 동의어 없음(비노출)
  한식당: "korean_food", 한식: "korean_food", 밥집: "korean_food", 국밥: "korean_food", 고깃집: "korean_food",
  중국집: "chinese_food", 중식당: "chinese_food", 중식: "chinese_food",
  일식당: "japanese_food", 일식: "japanese_food", 초밥: "japanese_food", 횟집: "japanese_food", 이자카야: "japanese_food",
  양식당: "western_food", 양식: "western_food", 파스타: "western_food", 레스토랑: "western_food", 피자: "western_food",
  분식집: "snack", 분식: "snack", 김밥: "snack", 떡볶이: "snack",
  호프집: "pub", 호프: "pub", 술집: "pub", 주점: "pub", 포차: "pub",
};

const AMOUNT = /(\d+(?:\.\d+)?)\s*(억|천만|천|만)/g;
const SCALE: Record<string, number> = { 억: 100_000_000, 천만: 10_000_000, 천: 10_000_000, 만: 10_000 };

/** 단위 붙은 첫 금액부터, 공백만 사이에 두고 이어지는 더 작은 단위를 합산 (1억 5천 → 1.5억). 맨숫자는 금액이 아니다. */
function parseBudget(text: string): number | null {
  const cleaned = text.replaceAll(",", "");
  let total: number | null = null, prevEnd = 0, prevScale = 0;
  for (const m of cleaned.matchAll(AMOUNT)) {
    const scale = SCALE[m[2]];
    if (total !== null && (cleaned.slice(prevEnd, m.index).trim() || scale >= prevScale)) break;
    total = (total ?? 0) + Math.round(Number(m[1]) * scale);
    prevEnd = (m.index ?? 0) + m[0].length; prevScale = scale;
  }
  return total;
}

const HOUR_BAND_KO: Record<string, string> = {
  "00_06": "새벽(00~06시)", "06_11": "아침(06~11시)", "11_14": "점심(11~14시)",
  "14_17": "오후(14~17시)", "17_21": "저녁(17~21시)", "21_24": "밤(21~24시)",
};
const BANDS = Object.keys(HOUR_BAND_KO);

/** 받침 유무로 은/는. 한글이 아니면 '는'. */
function topic(word: string): string {
  const last = word.charCodeAt(word.length - 1);
  if (last < 0xac00 || last > 0xd7a3) return `${word}는`;
  return (last - 0xac00) % 28 === 0 ? `${word}는` : `${word}은`;
}

export function intentDiagnosisOf(regionCode: string, industryId: string): IntentDiagnosis | null {
  const region = REGIONS.find((r) => r.region_code === regionCode);
  if (!region) return null;
  const profile = regionProfileOf(regionCode, LATEST_PROFILE_QUARTER);
  const type = neighborhoodTypeLabel(profile.neighborhood_type);
  const band = BANDS[hashSeed("peak", regionCode, industryId) % BANDS.length];
  const industryName = INDUSTRY_LABELS[industryId as IndustryId] ?? industryId;
  return {
    type_code: profile.neighborhood_type,
    type_name: type.name,
    time_label: profile.time_label,
    peak_sales_band: band,
    sentence: `${topic(region.name)} ${type.name}이고, ${topic(industryName)} ${HOUR_BAND_KO[band]}에 돈이 돕니다.`,
    year_quarter: LATEST_PROFILE_QUARTER,
    hour_gap_quarter: "20254",
  };
}

function withDiagnosis(r: IntentResult): IntentResult {
  const intent_type = r.region_code && r.industry_id ? "A" : r.region_code ? "B" : "C";
  const diagnosis = intent_type === "A" ? intentDiagnosisOf(r.region_code!, r.industry_id!) : null;
  return { ...r, intent_type, diagnosis };
}

/** 두 번째 형태 — 파서를 건너뛰고 진단만. */
export function intentOfCodes(regionCode: string, industryId: string): IntentResult {
  const region = REGIONS.find((r) => r.region_code === regionCode) ?? null;
  return withDiagnosis({
    intent_type: "A", region_code: region?.region_code ?? null, region_name: region?.name ?? null,
    district_code: region ? districtOf(region.region_code) : null, industry_id: industryId, budget_krw: null,
    missing: region ? ["budget"] : ["region", "budget"], candidates: [], diagnosis: null, source: "rule",
  });
}

/** 첫 번째 형태 — 문장 파싱. 규칙 경로 미러 + "홍대"만 LLM 경로 흉내. */
export function intentOfText(text: string): IntentResult {
  let regions: IntentCandidate[] = [];
  let districtCode: string | null = null;
  for (const name of REGION_NAMES_LONGEST_FIRST) {
    if (text.includes(name)) { regions = REGION_INDEX.get(name) ?? []; break; }
  }
  for (const [code, name] of DISTRICT_NAMES_LONGEST_FIRST) {
    if (text.includes(name)) { districtCode = code; break; }
  }
  if (regions.length > 1 && districtCode) regions = regions.filter((r) => r.district_code === districtCode);

  let source: IntentResult["source"] = "rule";
  if (regions.length === 0 && text.includes("홍대")) {
    // LLM 폴백 미러 — 랜드마크 한 건만
    regions = REGION_INDEX.get("서교동") ?? [];
    source = "llm";
  }

  const industry = Object.entries(INDUSTRY_SYNONYMS).find(([word]) => text.includes(word))?.[1] ?? null;
  const budget = parseBudget(text);
  const picked = regions.length === 1 ? regions[0] : null;
  const missing: IntentResult["missing"] = [];
  if (!picked) missing.push("region");
  if (!industry) missing.push("industry");
  if (!budget) missing.push("budget");

  return withDiagnosis({
    intent_type: "C",
    region_code: picked?.region_code ?? null,
    region_name: picked?.region_name ?? null,
    district_code: picked?.district_code ?? districtCode,
    industry_id: industry,
    budget_krw: budget,
    missing,
    candidates: regions.length > 1 ? regions : [],
    diagnosis: null,
    source,
  });
}

// ---------------------------------------------------------------------------
// 얼마나 버티나 · 시간대 어긋남 — 상세 계약 mock (무대 설계서 §5-2·§6-1)
// ---------------------------------------------------------------------------

const CHANGE_CODES: [string, string][] = [["LL", "다이나믹"], ["HH", "정체"], ["LH", "상권확장"], ["HL", "상권축소"]];
/** 서울 평균 — v0.32.0 실측(118·54)에 맞춘 고정값. */
const SEOUL_BASELINE = { operating_months: 118, closed_months: 54 };

/** 리포트 facts의 동별 상권 변화 상세 — 영업 개월 수를 결정적으로 만든다. */
export function commerceChangeDetailOf(regionCode: string, yearQuarter: string): RegionCommerceChangeDetail {
  const operating = Math.round(31 + unitFrom(hashSeed("operating_months", yearQuarter, regionCode)) * (206 - 31));
  const [change_code, change_name] = CHANGE_CODES[hashSeed("change", regionCode, yearQuarter) % CHANGE_CODES.length];
  return {
    region_code: regionCode,
    year_quarter: yearQuarter,
    change_code,
    change_name,
    operating_months: operating,
    closed_months: Math.round(operating * 0.45),
    seoul: SEOUL_BASELINE,
  };
}

export const LATEST_HOUR_GAP_QUARTER = "20254"; // 매출 원천은 프로필(20262)보다 두 분기 짧다

const BAND_HOURS = [6, 5, 3, 3, 4, 3];
/** 6구간 원값 → 시간당 강도(1.0 = 24시간 균등). 백엔드 hour_band.band_intensities와 같은 식. */
function intensities(values: number[]): number[] {
  const total = values.reduce((a, b) => a + b, 0);
  return values.map((v, i) => Number(((v / BAND_HOURS[i]) / (total / 24)).toFixed(3)));
}

/** 유형별 유동·매출 모양 — 실측 경향(업무형 낮 정점, 주거형 저녁·밤, 먹자형 저녁). 6구간 원값. */
const FOOTFALL_SHAPE: Record<string, number[]> = {
  office: [8, 20, 18, 18, 20, 6], campus: [10, 16, 15, 16, 22, 12], dining: [10, 14, 14, 16, 22, 14],
  hub: [12, 18, 14, 15, 20, 10], residential: [20, 16, 10, 10, 16, 14], mixed: [14, 16, 12, 12, 16, 10],
};
const SALES_SHAPE: Record<string, number[]> = {
  office: [1, 14, 40, 22, 16, 3], campus: [3, 8, 22, 18, 30, 15], dining: [4, 6, 18, 14, 34, 22],
  hub: [2, 12, 30, 22, 24, 6], residential: [3, 10, 20, 18, 32, 12], mixed: [3, 12, 26, 20, 26, 8],
};
/** 매출 원천이 없는 업종 — 리포트 facts에서 시간대 자료 없음으로 표시하는 조합. */
const NO_SALES_INDUSTRIES = new Set(["childcare"]);

export function hourGapOf(regionCode: string, industryId: string, yearQuarter: string): RegionIndustryHourGap | null {
  if (NO_SALES_INDUSTRIES.has(industryId)) return null;
  const type = regionProfileOf(regionCode, LATEST_PROFILE_QUARTER).neighborhood_type;
  const footfall = intensities(FOOTFALL_SHAPE[type] ?? FOOTFALL_SHAPE.mixed);
  const sales = intensities(SALES_SHAPE[type] ?? SALES_SHAPE.mixed);
  return {
    region_code: regionCode,
    industry_id: industryId,
    year_quarter: yearQuarter,
    bands: BANDS.map((hour_band, i) => ({
      hour_band, footfall_intensity: footfall[i], sales_intensity: sales[i],
      gap: Number((sales[i] - footfall[i]).toFixed(3)),
    })),
  };
}

/** 재무 프리필 — 실 API(§4-3 계약) 미러. 값은 결정적, basis·caveat 형태는 백엔드 응답과 같다.
 *  실측 규모(역삼1동 카페 월 2,613만·강남 권역 65.5천원/㎡)에 맞춘 범위. */
export function financePrefillOf(regionCode: string, industryId: string): FinancePrefill {
  const u = unitFrom(hashSeed("finance-prefill", regionCode, industryId));
  const storeCount = 40 + Math.floor(u * 600);
  const monthly = Math.round(9_000_000 + u * 20_000_000);
  const seoulMedianMonthly = Math.round(9_000_000 + unitFrom(hashSeed("finance-prefill-seoul-median", "20254", industryId)) * 20_000_000);
  const rent = Math.round((35 + u * 40) * 100) / 100;
  const COST: Record<string, number> = { cafe: 0.35, hair_salon: 0.25, gym: 0.15, billiard: 0.2, karaoke: 0.2, pc_bang: 0.2, academy: 0.3, childcare: 0.3, convenience_store: 0.7, real_estate: 0.1 };
  const hasSales = industryId !== "childcare"; // 어린이집은 매출 원천이 없다
  return {
    region_code: regionCode,
    industry_id: industryId,
    expected_monthly_revenue: {
      value: hasSales ? monthly : null,
      basis: hasSales
        ? { year_quarter: "20254", quarterly_sales: monthly * 3 * storeCount, store_count: storeCount, source_codes: ["CS100010"], seoul_median_monthly: seoulMedianMonthly }
        : { year_quarter: "", quarterly_sales: 0, store_count: 0, source_codes: [] },
      caveat: hasSales
        ? `이 동 같은 업종 ${storeCount}곳의 분기 매출을 점포 수로 나눈 평균입니다. 편차가 크고 신규 점포는 평균 아래서 시작하는 경우가 많습니다.`
        : "이 동네엔 이 업종의 매출 자료가 없습니다.",
      unit: "원/월",
    },
    rent_per_m2: {
      value: rent,
      basis: { region_path: "서울>강남", building_type: "medium_large", period: "2026Q2", level: "권역", small_per_m2: Math.round((rent - 1) * 100) / 100, source: "R-ONE" },
      caveat: "행정동 단위 임대료 자료가 없어 강남 권역(R-ONE, 중대형 상가) 평균입니다. 실제 매물과 다를 수 있습니다.",
      unit: "천원/㎡/월",
    },
    cost_ratio: { value: COST[industryId] ?? 0.4, basis: { kind: "industry_benchmark", industry_id: industryId }, caveat: "업종 평균 근사값입니다. 원가 구조를 알면 고치세요.", unit: null },
    loan_rate: { value: 0.0405, basis: { rate_type: "loan_facility", period: "202607", rate_pct: 4.05, source: "ECOS" }, caveat: "공시 평균 금리입니다. 실제 심사 금리와 다릅니다.", unit: "비율" },
    equity: null,
  };
}

/** 후보 공고 — 실 API(§3 결정론 필터) 미러. 서울 전용이 앞, 전국이 뒤. 마감 있는 것이 먼저. */
const CANDIDATE_SEEDS: { title: string; org: string; field: string; why: string; deadline: string | null }[] = [
  { title: "[서울] 2026년 하반기 소상공인 경영개선 자금 지원", org: "서울특별시", field: "금융", why: "서울 · 소상공인 · 금융", deadline: "2026-10-31" },
  { title: "[서울] 2026년 청년창업기업 전문상담 경영 지원", org: "서울특별시", field: "경영", why: "서울 · 창업 · 경영", deadline: "2026-11-14" },
  { title: "[서울] 2026년 골목상권 디지털 전환 지원사업", org: "서울특별시", field: "경영", why: "서울 · 소상공인 · 경영", deadline: "2026-12-05" },
  { title: "2026년 중소벤처기업부 소상공인 정책자금 융자사업", org: "중소벤처기업부", field: "금융", why: "전국 · 소상공인 · 금융", deadline: null },
  { title: "2026년 소상공인 투자연계 지원사업 립스(LIPS) 프로그램", org: "중소벤처기업부", field: "금융", why: "전국 · 소상공인 · 금융", deadline: null },
  { title: "2026년 예비창업패키지 창업기업 모집", org: "중소벤처기업부", field: "창업", why: "전국 · 예비창업 · 창업", deadline: "2026-10-20" },
  { title: "2026년 우리동네 크라우드펀딩 지원사업", org: "중소벤처기업부", field: "금융", why: "전국 · 소상공인 · 금융", deadline: null },
  { title: "2026년 소상공인 비즈플러스카드 지원사업", org: "중소벤처기업부", field: "금융", why: "전국 · 소상공인 · 금융", deadline: null },
];

export function fundingCandidatesOf(stage: string | null): FundingCandidate[] {
  // pre(등록 전)는 창업 공고가, registered는 소상공인 공고가 앞선다 — 실 API의 가중과 같은 방향.
  const weight = (why: string) => (stage === "pre" ? (why.includes("창업") ? 0 : 1) : why.includes("소상공인") ? 0 : 1);
  return [...CANDIDATE_SEEDS]
    .sort((a, b) => weight(a.why) - weight(b.why))
    .map((seed, i) => ({
      program_id: `mock-${i + 1}`,
      source: "bizinfo",
      title: seed.title,
      org: seed.org,
      url: `https://www.bizinfo.go.kr/mock/${i + 1}`,
      apply_period: seed.deadline ? `2026-09-01 ~ ${seed.deadline}` : "상시",
      exec_org: null,
      field_category: seed.field,
      field_subcategory: null,
      target_text: seed.why.includes("예비창업") ? "예비창업자" : "소상공인",
      hashtags: null,
      apply_begin: "2026-09-01",
      deadline: seed.deadline,
      summary: null,
      is_expired: false,
      why: seed.why,
    }));
}

/** 창업 지원 정보 — 실 API처럼 금융은 대출 묶음, 구 이름이 든 공고는 구 묶음, 나머지는 창업·경영 묶음. */
export function supportGuideOf(regionCode: string | null, industryId: string | null): SupportGuide {
  const districtName = regionCode ? SEOUL_DISTRICTS[districtOf(regionCode)] ?? null : null;
  const items: SupportItem[] = fundingCandidatesOf(null).map((c) => ({ ...c, district_match: false, industry_match: false }));
  const districtItems: SupportItem[] = districtName ? [
    { ...items[1], program_id: "mock-district-1", title: `[서울] ${districtName} 2026년 소상공인 원스톱 지원사업`, why: "서울 · 소상공인 · 경영", district_match: true },
    { ...items[1], program_id: "mock-district-2", title: `[서울] ${districtName} 2026년 소규모 자영업자 간판 설치 지원`, why: "서울 · 소상공인 · 경영", district_match: true },
  ] : [];
  const others = items.filter((c) => c.field_category !== "금융").map((c, i) => (i === 0 && industryId ? { ...c, industry_match: true } : c));
  return {
    region_code: regionCode,
    district_name: districtName,
    industry_id: industryId,
    loans: items.filter((c) => c.field_category === "금융"),
    district: districtItems,
    others,
    rates: [
      { rate_type: "base", period: "202608", rate_pct: 3.0 },
      { rate_type: "loan_facility", period: "202608", rate_pct: 4.05 },
    ],
  };
}

/** 확인할 질문 초안 — 실 API(§4 규칙 목록)의 발화 조건을 흉내 낸다. 금액은 만원 단위 문장. */
export function planQuestionsOf(body: {
  input: Record<string, number>;
  unconfirmed?: string[];
  prefilled?: string[];
  candidate_titles?: string[];
  profile?: { business_registered?: boolean | null; guarantee_status?: string; policy_confirmation_status?: string };
}): PlanQuestion[] {
  const i = body.input;
  const manwon = (won: number) => Math.round(won / 10_000).toLocaleString("ko-KR");
  const capex = i.deposit + i.key_money + i.interior_cost + i.equipment_cost;
  const fixed = i.monthly_rent + Math.round((i.desired_loan * i.loan_rate) / 12) + i.monthly_insurance + i.monthly_payroll;
  const total = capex + fixed * 6;
  const external = Math.max(0, total - i.equity);
  const gap = Math.max(0, total - i.equity - i.desired_loan);
  const profile = body.profile ?? {};
  const questions: PlanQuestion[] = [];

  if (external > 0) questions.push({ text: `자기자본 외 ${manwon(external)}만 원을 어떤 경로(보증·대출·정책자금)로 나눠 조달할 수 있는지`, basis: `조달 필요 ${external.toLocaleString("ko-KR")}원 > 0`, kind: "gap" });
  if (gap > 0) questions.push({ text: `희망대출 ${manwon(i.desired_loan)}만 원이 실행돼도 ${manwon(gap)}만 원이 남습니다. 추가 조달과 비용 축소 중 무엇이 현실적인지`, basis: `부족액 ${gap.toLocaleString("ko-KR")}원 > 0`, kind: "gap" });
  if (i.desired_loan > 0) questions.push({ text: `희망대출 ${manwon(i.desired_loan)}만 원의 예상 금리·기간·상환 방식`, basis: `공시 평균 금리 ${(i.loan_rate * 100).toFixed(2)}%로 계산`, kind: "assumption" });
  for (const field of body.unconfirmed ?? []) questions.push({ text: `${field}은(는) 아직 확인하지 않은 값입니다(0원이 아닙니다). 견적을 받아야 하는지`, basis: `미입력 항목 ${field}`, kind: "assumption" });
  if ((body.prefilled ?? []).includes("expected_monthly_revenue")) questions.push({ text: "예상 월매출은 이 동 같은 업종 평균입니다. 신규 점포 기준으로 낮춰 잡아야 하는지", basis: "월매출이 실측 프리필 그대로", kind: "assumption" });
  if ((body.prefilled ?? []).includes("monthly_rent")) questions.push({ text: "월세는 권역 평균 기준입니다. 실제 매물 조건으로 다시 계산해야 하는지", basis: "월세가 권역 근사 그대로", kind: "assumption" });
  if (profile.business_registered == null) questions.push({ text: "사업자등록 전인지 후인지에 따라 지원 대상이 달라집니다 — 어느 쪽인지", basis: "사업자등록 여부 미확인", kind: "procedure" });
  if ((profile.guarantee_status ?? "unknown") === "unknown") questions.push({ text: "보증기관(서울신용보증재단) 보증서 발급 절차와 소요 기간", basis: "보증서 진행 상태 미확인", kind: "procedure" });
  if ((profile.policy_confirmation_status ?? "unknown") === "unknown") questions.push({ text: "소상공인 정책자금 확인서가 필요한지, 필요하다면 발급 절차", basis: "확인서 진행 상태 미확인", kind: "procedure" });
  for (const title of (body.candidate_titles ?? []).slice(0, 3)) questions.push({ text: `「${title}」에 해당하는지, 은행 대출과 병행 가능한지`, basis: "후보 공고", kind: "procedure" });

  return questions;
}

// ---------------------------------------------------------------------------
// 판정 카드 mock — 설계서 2026-09-28-verdict-card-design §3. 판정 규칙은 백엔드 rules.py를 그대로 옮긴 것
// (보류 우선 → strong 2+ red → on 1+ orange → clear). 값·근거는 해시 기반 결정적.
// ---------------------------------------------------------------------------

// 업종별 판정 원천 — 백엔드 dependencies의 sources 미러 (업종 특화 신호 설계서 §4). 판정 대상 여부는 isVerdictIndustry가 정한다.
const BASIS_BY_INDUSTRY: Partial<Record<string, VerdictBasis>> = { convenience_store: "proxy", real_estate: "aggregate" };
// 백엔드 profiles.py 미러 — 원천별 신호 순서
const SIGNAL_KEYS_BY_BASIS: Record<VerdictBasis, VerdictSignalKey[]> = {
  permit: ["net_outflow", "survival_cliff", "early_closure", "saturation"],
  proxy: ["net_outflow", "survival_cliff", "early_closure", "saturation", "tobacco_gap"],
  aggregate: ["closure_rate", "survival_cliff", "early_closure", "saturation", "trade_per_office"],
};
// 원천 표기 교체 (SourcedSignal 미러) — 없는 키는 SIGNAL_SOURCE 기본값
const SOURCE_BY_BASIS: Record<VerdictBasis, Partial<Record<VerdictSignalKey, VerdictSignalSource>>> = {
  permit: {},
  proxy: { net_outflow: "tobacco", survival_cliff: "tobacco", early_closure: "tobacco", saturation: "tobacco" },
  aggregate: { survival_cliff: "commerce", early_closure: "commerce", saturation: "commerce" },
};
// 원천이 재료를 주지 않는 신호 (UnsupportedSignal 미러)
const UNSUPPORTED_BY_BASIS: Record<VerdictBasis, ReadonlySet<VerdictSignalKey>> = {
  permit: new Set(), proxy: new Set(), aggregate: new Set(["survival_cliff", "early_closure"]),
};
const UNSUPPORTED_EVIDENCE = "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음";
const SIGNAL_SOURCE: Record<VerdictSignalKey, VerdictSignalSource> = {
  net_outflow: "store", survival_cliff: "store", early_closure: "store", saturation: "metric",
  closure_rate: "commerce", tobacco_gap: "tobacco", trade_per_office: "molit",
};

const SIGNAL_BAND_WORDS: Record<VerdictSignalKey, [string, string, string]> = {
  net_outflow: ["순유출", "많은", "적은"],
  survival_cliff: ["생존율", "낮은", "높은"],
  early_closure: ["폐업 점포 영업 기간", "짧은", "긴"],
  saturation: ["밀집", "높은", "낮은"],
  closure_rate: ["폐업률", "높은", "낮은"],
  tobacco_gap: ["담배소매인 반경 안 상가 비율", "높은", "낮은"],
  trade_per_office: ["사무소당 거래", "적은", "많은"],
};
const VERDICT_BANDS: [number, VerdictBand][] = [
  [90, "very_bad"], [75, "bad"], [25, "normal"], [10, "good"], [0, "very_good"],
];

/** 판정 대상 여부 — 실 API의 EXCLUDED_INDUSTRIES 미러 = 프론트 INDUSTRIES 14종 − 편의점·부동산(shared/verdict.ts 단일 원천). */
export function isJudgedIndustry(industryId: string): industryId is IndustryId {
  return isVerdictIndustry(industryId);
}

function signalOf(key: VerdictSignalKey, regionCode: string, industryId: string, basis: VerdictBasis): VerdictSignal {
  const source = SOURCE_BY_BASIS[basis][key] ?? SIGNAL_SOURCE[key];
  if (UNSUPPORTED_BY_BASIS[basis].has(key)) {
    return { key, level: "unavailable", value: null, percentile: null, band: null, band_label: null, evidence: UNSUPPORTED_EVIDENCE, source };
  }
  const u = unitFrom(hashSeed("verdict", key, regionCode, industryId));
  const name = INDUSTRY_LABELS[industryId as IndustryId] ?? industryId;
  // 하위 8%는 미판정(표본 부족), 나머지 92%를 0~100 백분위로 펼친다 — strong(≥90)·red가 실제로 나온다
  if (u < 0.08) {
    return { key, level: "unavailable", value: null, percentile: null, band: null, band_label: null, evidence: `표본 부족 — 3년 전 개업 코호트 ${Math.floor(u * 100)}곳 (10곳 미만)`, source };
  }
  const percentile = Math.round(((u - 0.08) / 0.92) * 1000) / 10; // 0.0 ~ 100.0
  const level = percentile >= 90 ? "strong" : percentile >= 75 ? "on" : "off";
  const top = Math.max(1, Math.round(100 - percentile));
  const EVIDENCE: Record<VerdictSignalKey, string> = {
    net_outflow: `지난 12개월 폐업 ${20 + Math.floor(u * 30)}곳, 개업 ${15 + Math.floor(u * 10)}곳 (순유출률 +${Math.round(u * 20)}%)`,
    survival_cliff: `3년 전 개업한 ${name} 40곳 중 ${40 - Math.floor(u * 25)}곳만 남음 (생존율 ${100 - Math.round(u * 62)}%)`,
    early_closure: `최근 3년 폐업 ${name}의 영업 기간 중위 ${36 - Math.round(u * 20)}개월`,
    saturation: `상주인구 1,000명당 ${name} ${(2 + u * 9).toFixed(1)}곳`,
    closure_rate: `지난 4분기 폐업 ${5 + Math.floor(u * 30)}곳 (4분기 전 점포 ${60 + Math.floor(u * 100)}곳의 ${Math.round(u * 8)}%, 서울시 상권분석 집계)`,
    tobacco_gap: `이 동 상가 자리 ${300 + Math.floor(u * 900)}곳 중 ${50 + Math.round(u * 30)}%가 영업 중인 담배소매인 50m 안 — 새 담배소매인 지정이 어렵다`,
    trade_per_office: `지난 12개월 아파트 매매 ${100 + Math.floor(u * 400)}건 ÷ 중개사무소 ${40 + Math.floor(u * 60)}곳 = 사무소당 ${(1 + u * 6).toFixed(1)}건 (국토부 실거래가)`,
  };
  const value = Math.round(u * 100) / 100;
  const band = VERDICT_BANDS.find(([min]) => percentile >= min)![1];
  const [subject, bad, good] = SIGNAL_BAND_WORDS[key];
  const labels: Record<VerdictBand, string> = {
    very_bad: `매우 ${bad} 편`, bad: `${bad} 편`, normal: "보통", good: `${good} 편`, very_good: `매우 ${good} 편`,
  };
  const band_label = `${subject} ${labels[band]}`;
  const evidence = `${EVIDENCE[key]} — ${band_label}(서울 ${name} 동을 100곳으로 치면 ${bad} 쪽에서 ${top}번째쯤)`;
  return { key, level, value, percentile, band, band_label, evidence, source };
}

function judgeOf(signals: VerdictSignal[]): VerdictCode {
  const judging = signals.filter((s) => !ADVISORY_SIGNAL_KEYS.has(s.key));
  const evaluable = judging.filter((s) => s.level !== "unavailable").length;
  const strong = judging.filter((s) => s.level === "strong").length;
  const on = judging.filter((s) => s.level === "on" || s.level === "strong").length;
  if (evaluable < 2) return "insufficient";
  if (strong >= 2) return "red";
  if (on >= 1) return "orange";
  return "clear";
}

export function verdictOf(regionCode: string, industryId: string): RegionIndustryVerdict {
  const basis = BASIS_BY_INDUSTRY[industryId] ?? "permit";
  const signals = SIGNAL_KEYS_BY_BASIS[basis].map((key) => signalOf(key, regionCode, industryId, basis));
  const judging = signals.filter((s) => !ADVISORY_SIGNAL_KEYS.has(s.key));
  return {
    region_code: regionCode,
    industry_id: industryId,
    verdict_code: judgeOf(signals),
    basis,
    strong_count: judging.filter((s) => s.level === "strong").length,
    on_count: judging.filter((s) => s.level === "on" || s.level === "strong").length,
    signals,
    computed_at: "2026-09-29T04:30:00+09:00",
  };
}

// 대안 두 축 — 백엔드 domain/services/alternatives.py의 순위 규칙을 그대로 옮긴 것 (설계서 §12).
// 후보는 clear·orange만, 키 (판정 순위, strong, on)가 기준보다 작은 것만, 키→id 순으로 3개.
const VERDICT_RANK: Record<VerdictCode, number> = { clear: 0, orange: 1, red: 2, insufficient: 3 };
const ALTERNATIVE_LIMIT = 3;

function signalKey(v: RegionIndustryVerdict): [number, number, number] {
  return [VERDICT_RANK[v.verdict_code], v.strong_count, v.on_count];
}

function keyLess(a: number[], b: number[]): boolean {
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] < b[i];
  return false;
}

function rankAlternatives(base: RegionIndustryVerdict, candidates: RegionIndustryVerdict[], id: (v: RegionIndustryVerdict) => string): RegionIndustryVerdict[] {
  const baseKey = signalKey(base);
  return candidates
    .filter((v) => (v.verdict_code === "clear" || v.verdict_code === "orange") && keyLess(signalKey(v), baseKey))
    .sort((a, b) => (keyLess(signalKey(a), signalKey(b)) ? -1 : keyLess(signalKey(b), signalKey(a)) ? 1 : id(a).localeCompare(id(b))))
    .slice(0, ALTERNATIVE_LIMIT);
}

export function alternativesOf(regionCode: string, industryId: string): VerdictAlternatives {
  const base = verdictOf(regionCode, industryId);
  const neighborhoodType = regionProfileOf(regionCode, LATEST_PROFILE_QUARTER).neighborhood_type;
  const sameRegion = INDUSTRIES.filter((id) => id !== industryId && isJudgedIndustry(id)).map((id) => verdictOf(regionCode, id));
  const sameType = REGIONS
    .filter((r) => r.region_code !== regionCode && regionProfileOf(r.region_code, LATEST_PROFILE_QUARTER).neighborhood_type === neighborhoodType)
    .map((r) => verdictOf(r.region_code, industryId));
  const nameOf = (code: string) => REGIONS.find((r) => r.region_code === code)?.name ?? code;
  return {
    region_code: regionCode,
    industry_id: industryId,
    neighborhood_type: neighborhoodType,
    industries: rankAlternatives(base, sameRegion, (v) => v.industry_id).map((v) => ({
      industry_id: v.industry_id, industry_name: INDUSTRY_LABELS[v.industry_id as IndustryId] ?? v.industry_id,
      verdict_code: v.verdict_code, strong_count: v.strong_count, on_count: v.on_count,
    })),
    regions: rankAlternatives(base, sameType, (v) => v.region_code).map((v) => ({
      region_code: v.region_code, region_name: nameOf(v.region_code),
      verdict_code: v.verdict_code, strong_count: v.strong_count, on_count: v.on_count,
    })),
  };
}

export function verdictRows(industryId: string): VerdictRow[] {
  return REGIONS.map(({ region_code }) => ({ region_code, value: verdictOf(region_code, industryId).verdict_code }));
}
