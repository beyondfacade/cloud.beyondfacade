import { readFileSync } from "node:fs";
import path from "node:path";
import type { FeatureCollection, MultiPolygon } from "geojson";
import type {
  AgentEvent,
  AgentName,
  ChildcareCenter,
  ChildcareRegionSummary,
  ConvenienceRegionSummary,
  ConvenienceStore,
  MetricKey,
  MetricRow,
  RegionProfile,
  RegionSummary,
  Store,
  SummaryCard,
} from "@/shared/api/types";
import { STORE_SAMPLES } from "./store-samples";

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
  };
}
