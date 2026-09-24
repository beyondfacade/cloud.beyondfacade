import { readFileSync } from "node:fs";
import path from "node:path";
import type { FeatureCollection, MultiPolygon } from "geojson";
import type {
  AgentEvent,
  AgentName,
  CategoryRow,
  ChildcareCenter,
  FinancePrefill,
  FundingCandidate,
  PlanQuestion,
  ChildcareRegionSummary,
  ConvenienceRegionSummary,
  IntentCandidate,
  IntentDiagnosis,
  IntentResult,
  ConvenienceStore,
  MetricKey,
  MetricRow,
  CommerceChangeMetricKey,
  ProfileMetricKey,
  RegionCommerceChangeDetail,
  RegionIndustryHourGap,
  RegionProfile,
  RegionSummary,
  Store,
  SummaryCard,
} from "@/shared/api/types";
import { availableYears, isMetricMissingForIndustry } from "@/features/map-explorer/lib/metric-coverage";
import { STORE_SAMPLES } from "./store-samples";
import { INDUSTRY_LABELS, type IndustryId } from "@/shared/industries";
import { neighborhoodTypeLabel } from "@/shared/neighborhood";
import { SEOUL_DISTRICTS, districtOf } from "@/shared/seoul-districts";

type RegionProperties = { region_code: string; name: string };

/** 서울 행정동 427개 실경계 — 백엔드 GET /regions/geojson 산출물 스냅샷 (v0.8.0, 좌표 5자리 절삭).
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
  if (isMetricMissingForIndustry(metric, industry)) return [];
  if (!availableYears(metric, industry).includes(year)) return [];
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

/** region_code·industry_id로 STORE_SAMPLES를 필터링해 마커용 점포 목록을 반환한다.
 *  실적재 데이터가 없는 업종/동 조합은 빈 배열 — 이는 오류가 아니라 실데이터 부재를 그대로 반영한 것. */
export function storesOf(regionCode: string, industryId: string): Store[] {
  const samples = STORE_SAMPLES[regionCode] ?? [];
  return samples
    .filter((s) => s.industry_id === industryId)
    .map(({ store_id, name, lat, lng, status_name, open_date }) => ({
      store_id,
      name,
      lat,
      lng,
      status_name,
      open_date,
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

/** childcareCentersOf 합산 — 실 API의 ChildcareRegionSummary.of 규칙과 동일. */
export function childcareSummaryOf(regionCode: string): ChildcareRegionSummary {
  const centers = childcareCentersOf(regionCode);
  const capacity = centers.reduce((sum, c) => sum + c.capacity, 0);
  const childCount = centers.reduce((sum, c) => sum + c.child_count, 0);
  const waitings = centers.map((c) => c.waiting_count).filter((w): w is number => w !== null);
  return {
    region_code: regionCode,
    base_date: centers.length > 0 ? "2026-09-17" : null,
    center_count: centers.length,
    capacity,
    child_count: childCount,
    occupancy_rate: capacity > 0 ? Math.round((childCount / capacity) * 10000) / 10000 : null,
    waiting_count: waitings.length > 0 ? waitings.reduce((sum, w) => sum + w, 0) : null,
  };
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

const AGENT_TOOLS: Record<Exclude<AgentName, "orchestrator">, { tool: string; summary: string }[]> = {
  market: [
    { tool: "closure_rate_lookup", summary: "강남구 카페 폐업률 조회" },
    { tool: "sales_trend_lookup", summary: "인근 상권 매출 데이터 조회" },
  ],
  shock: [
    { tool: "interest_rate_history", summary: "금리 변동 이력 조회" },
    { tool: "commodity_index_lookup", summary: "원두 가격 지수 조회" },
    { tool: "supply_chain_news", summary: "원두 공급망 뉴스 스캔" },
  ],
  funding: [
    { tool: "policy_fund_catalog", summary: "소상공인 정책자금 목록 조회" },
    { tool: "rent_market_lookup", summary: "임대료 시세 데이터 조회" },
  ],
};

const CALCULATOR_MARKDOWN = [
  "### 월세 vs 매입 비교",
  "",
  "| 구분 | 월세 (보증금 5,000만원 + 월 300만원) | 매입 (10억원, 대출 70%) |",
  "|---|---|---|",
  "| 초기 투자금 | 5,000만원 | 3억원 |",
  "| 월 고정비 | 300만원 | 대출이자 약 175만원 (연 3.5%) |",
  "| 5년 누적 비용 | 1억 8,500만원 | 1억 500만원 + 대출 원금 상환 |",
  "| 자산 형성 | 없음 | 부동산 자산 10억원 (시세 변동 별도) |",
].join("\n");

/** 발표 시연용 에이전트 이벤트 스크립트 — orchestrator → market/shock/funding → 리포트 → 완료. */
export function agentEventScript(): AgentEvent[] {
  const events: AgentEvent[] = [{ type: "agent_status", agent: "orchestrator", status: "running" }];

  (Object.keys(AGENT_TOOLS) as Exclude<AgentName, "orchestrator">[]).forEach((agent) => {
    events.push({ type: "agent_status", agent, status: "running" });
    for (const { tool, summary } of AGENT_TOOLS[agent]) {
      events.push({ type: "tool_call", agent, tool, summary });
    }
    events.push({ type: "agent_status", agent, status: "done" });
  });

  events.push(
    {
      type: "report_delta",
      section: "verdict",
      markdown: "### 종합 진단\n\n강남구 카페 상권은 **안정적 성장세**이나 원두 가격 상승발 원가 압박이 존재합니다.",
    },
    {
      type: "report_delta",
      section: "market",
      markdown: "### 상권 진단\n\n최근 1년 신규 카페 개업이 12% 증가했고, 폐업률은 6.4%로 서울 평균 대비 낮습니다.",
    },
    {
      type: "report_delta",
      section: "shock",
      markdown: "### 충격 분석\n\n기준금리는 동결 기조지만 원두 원가는 전년 대비 8% 상승 — 마진 압박 요인입니다.",
    },
    {
      type: "report_delta",
      section: "funding",
      markdown: "### 정책자금\n\n소상공인 정책자금(최대 7,000만원, 금리 2.5%) 신청 조건을 충족합니다.",
    },
    { type: "report_delta", section: "calculator", markdown: CALCULATOR_MARKDOWN },
  );

  events.push(
    { type: "agent_status", agent: "orchestrator", status: "done" },
    {
      type: "report_done",
      report_id: "mock-report-001",
      citations: [
        { title: "서울시 상권분석 서비스 — 강남구 폐업률 통계", url: "https://data.seoul.go.kr", grade: "fact" },
        { title: "소상공인시장진흥공단 정책자금 공고", url: "https://semas.or.kr", grade: "fact" },
        { title: "국제 원두 선물 가격 동향 리포트", url: "https://example-news.com/coffee-price", grade: "fact" },
        { title: "강남 카페 상권 SNS 언급량 분석", url: "https://example-news.com/sns-trend", grade: "signal" },
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
    office: `직장인구가 상주인구의 ${ratio.toFixed(1)}배로 서울 상위 10%이고, 주말 유동이 평일보다 적습니다.`,
    campus: `대학 시설이 있고, 거리 위 20대 비중이 ${(share20s * 100).toFixed(1)}%로 서울 상위 10%입니다.`,
    dining: `결제액의 ${(fnbShare * 100).toFixed(1)}%가 음식·유흥이고, 낮 시간 유동이 서울 상위 25%입니다.`,
    hub: `집객시설이 ${facility}개로 서울 상위 25%이고, 낮 시간 유동이 밤보다 강합니다.`,
    residential: "직장인구가 상주인구보다 적고, 밤 시간 체류가 서울 하위 25%에 들지 않습니다.",
    mixed: "어느 축에서도 서울 상위·하위 경계를 넘지 않습니다.",
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

/** 동 단위 분기 지표 — 실측 분포(최소 31 · 중앙 117 · 최대 206개월)에 맞춰 결정적으로 만든다. */
const REGION_METRIC_RANGES: Record<CommerceChangeMetricKey, [number, number]> = {
  operating_months: [31, 206],
};

export const LATEST_CHANGE_QUARTER = "20262";

export function changeMetricRows(metric: CommerceChangeMetricKey, yearQuarter: string): MetricRow[] {
  const [min, max] = REGION_METRIC_RANGES[metric];
  return REGIONS.map(({ region_code }) => ({
    region_code,
    value: Math.round(min + unitFrom(hashSeed(metric, yearQuarter, region_code)) * (max - min)),
  }));
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

/** 유형 단계구분도 — 실 API `GET /profiles/types` 미러. 프로필 픽스처의 유형을 그대로 쓴다(결정적). */
/** 파생 지표 숫자 단계구분도 — 단일 프로필과 같은 원천(regionProfileOf)이라 두 계약이 어긋나지 않는다.
 *  값이 null인 동은 행을 만들지 않는다(실 API 계약: 0으로 내보내면 지도가 거짓말한다). */
export function profileMetricRows(metric: ProfileMetricKey, yearQuarter: string): MetricRow[] {
  return REGIONS.flatMap(({ region_code }) => {
    const value = regionProfileOf(region_code, yearQuarter)[metric];
    return value === null ? [] : [{ region_code, value }];
  });
}

export function profileTypeRows(yearQuarter: string): CategoryRow[] {
  return REGIONS.map(({ region_code }) => ({
    region_code,
    type_code: regionProfileOf(region_code, yearQuarter).neighborhood_type,
  }));
}

// ---------------------------------------------------------------------------
// 얼마나 버티나 · 시간대 어긋남 — 상세 계약 mock (무대 설계서 §5-2·§6-1)
// ---------------------------------------------------------------------------

const CHANGE_CODES: [string, string][] = [["LL", "다이나믹"], ["HH", "정체"], ["LH", "상권확장"], ["HL", "상권축소"]];
/** 서울 평균 — v0.32.0 실측(118·54)에 맞춘 고정값. */
const SEOUL_BASELINE = { operating_months: 118, closed_months: 54 };

/** 동별 상권 변화 상세 — 단계구분도(`changeMetricRows`)와 같은 해시라 지도 색과 패널 숫자가 어긋나지 않는다. */
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
/** 매출 원천이 없는 업종 — 실 API가 404 `HOUR_GAP_NOT_FOUND`를 주는 조합. */
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
  const rent = Math.round((35 + u * 40) * 100) / 100;
  const COST: Record<string, number> = { cafe: 0.35, hair_salon: 0.25, gym: 0.15, billiard: 0.2, karaoke: 0.2, pc_bang: 0.2, academy: 0.3, childcare: 0.3, convenience_store: 0.7, real_estate: 0.1 };
  const hasSales = industryId !== "childcare"; // 어린이집은 매출 원천이 없다
  return {
    region_code: regionCode,
    industry_id: industryId,
    expected_monthly_revenue: {
      value: hasSales ? monthly : null,
      basis: hasSales
        ? { year_quarter: "20254", quarterly_sales: monthly * 3 * storeCount, store_count: storeCount, source_codes: ["CS100010"] }
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
