import type { FeatureCollection, Polygon } from "geojson";
import type {
  AgentEvent,
  AgentName,
  MetricKey,
  MetricRow,
  RegionSummary,
  SummaryCard,
} from "@/shared/api/types";

type RegionProperties = { region_code: string; name: string };

/** 강남권 행정동 8개 — 실좌표 기반 그리드 (사각형, mock 폴리곤). */
const DONGS: { region_code: string; name: string; lng1: number; lat1: number; lng2: number; lat2: number }[] = [
  { region_code: "1168064000", name: "역삼1동", lng1: 127.02, lat1: 37.49, lng2: 127.0325, lat2: 37.51 },
  { region_code: "1168065000", name: "역삼2동", lng1: 127.0325, lat1: 37.49, lng2: 127.045, lat2: 37.51 },
  { region_code: "1168058500", name: "대치1동", lng1: 127.045, lat1: 37.49, lng2: 127.0575, lat2: 37.51 },
  { region_code: "1168060000", name: "대치4동", lng1: 127.0575, lat1: 37.49, lng2: 127.07, lat2: 37.51 },
  { region_code: "1168052100", name: "논현1동", lng1: 127.02, lat1: 37.51, lng2: 127.0325, lat2: 37.53 },
  { region_code: "1168056500", name: "삼성1동", lng1: 127.0325, lat1: 37.51, lng2: 127.045, lat2: 37.53 },
  { region_code: "1168057000", name: "삼성2동", lng1: 127.045, lat1: 37.51, lng2: 127.0575, lat2: 37.53 },
  { region_code: "1168055500", name: "청담동", lng1: 127.0575, lat1: 37.51, lng2: 127.07, lat2: 37.53 },
];

function rectPolygon(lng1: number, lat1: number, lng2: number, lat2: number): Polygon {
  return {
    type: "Polygon",
    coordinates: [
      [
        [lng1, lat1],
        [lng2, lat1],
        [lng2, lat2],
        [lng1, lat2],
        [lng1, lat1],
      ],
    ],
  };
}

export const SEOUL_SAMPLE_GEOJSON: FeatureCollection<Polygon, RegionProperties> = {
  type: "FeatureCollection",
  features: DONGS.map(({ region_code, name, lng1, lat1, lng2, lat2 }) => ({
    type: "Feature",
    properties: { region_code, name },
    geometry: rectPolygon(lng1, lat1, lng2, lat2),
  })),
};

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

export function metricRows(metric: MetricKey, year: number): MetricRow[] {
  const [min, max] = METRIC_RANGES[metric];
  return DONGS.map(({ region_code }) => {
    const u = unitFrom(hashSeed(metric, year, region_code));
    const raw = min + u * (max - min);
    const value = metric === "store_count" ? Math.round(raw) : Math.round(raw * 1000) / 1000;
    return { region_code, value };
  });
}

export function summaryOf(code: string, industry: string): RegionSummary {
  const dong = DONGS.find((d) => d.region_code === code);
  const name = dong?.name ?? "알 수 없음";
  const storeCount = metricRows("store_count", 2026).find((r) => r.region_code === code)?.value ?? 0;
  const closureRate = metricRows("closure_rate", 2026).find((r) => r.region_code === code)?.value ?? 0;
  const growthRate = metricRows("growth_rate", 2026).find((r) => r.region_code === code)?.value ?? 0;
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
