/** 공식 상담·신청 창구 — 공고 목록(기업마당)에 없는 상시 창구라 화면이 직접 안내한다. 주소는 2026-09-30 접속 확인. */
export const SUPPORT_CHANNELS: readonly { name: string; description: string; url: string }[] = [
  { name: "소상공인 정책자금", description: "중소벤처기업부 소상공인 정책자금(융자) 신청과 자금별 조건 확인", url: "https://ols.sbiz.or.kr" },
  { name: "서울신용보증재단", description: "서울 소상공인이 은행 대출을 받을 때 필요한 보증 상담·신청", url: "https://www.seoulshinbo.co.kr" },
  { name: "서울시 자영업지원센터", description: "창업·경영 교육과 1:1 컨설팅 신청", url: "https://www.seoulsbdc.or.kr" },
  { name: "소상공인24", description: "소상공인 지원사업 통합 조회·신청", url: "https://www.sbiz24.kr" },
  { name: "K-스타트업", description: "예비창업패키지 등 정부 창업지원사업 공고·신청", url: "https://www.k-startup.go.kr" },
  { name: "기업마당", description: "정부·지자체 지원사업 공고 전체 검색", url: "https://www.bizinfo.go.kr" },
];

const RATE_LABELS: Record<string, string> = {
  base: "한국은행 기준금리",
  loan_facility: "은행 시설자금대출 평균 금리",
};

export function rateLabel(rateType: string): string {
  return RATE_LABELS[rateType] ?? rateType;
}

/** "202608" → "2026년 8월". 형식이 다르면 원문 그대로. */
export function formatPeriod(period: string): string {
  const match = /^(\d{4})(\d{2})$/.exec(period);
  return match ? `${match[1]}년 ${Number(match[2])}월` : period;
}

export function formatRate(ratePct: number): string {
  return `연 ${ratePct.toFixed(2)}%`;
}
