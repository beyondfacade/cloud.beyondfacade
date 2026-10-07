// 입력 다양화 (testplan §2) — 한 동만 반복하면 DB 캐시가 다 맞아 실제보다 빠르게 나온다.
// 동 목록은 프론트 정적 경계 파일(427개)에서, 업종은 판정 대상 12개(편의점·부동산은 판정 제외라 지도가 판정을 안 부른다).
import { SharedArray } from 'k6/data';

export const BASE = __ENV.BASE || 'http://localhost:8202';   // 부하 테스트 컨테이너(scripts/load/env.sh)

export const REGIONS = new SharedArray('regions', () =>
  JSON.parse(open('../../../frontend/public/geojson/seoul-regions.geojson')).features.map((f) => f.properties));

export const INDUSTRIES = [
  ['korean_food', '한식'], ['chinese_food', '중식'], ['japanese_food', '일식'], ['western_food', '양식'],
  ['snack', '분식'], ['pub', '호프·주점'], ['cafe', '카페'], ['hair_salon', '미용실'],
  ['karaoke', '노래방'], ['pc_bang', 'PC방'], ['gym', '헬스장'], ['billiard', '당구장'],
];

const pick = (list) => list[Math.floor(Math.random() * list.length)];

export function pickPair() {
  const region = pick(REGIONS);
  const [industry, label] = pick(INDUSTRIES);
  return { region: region.region_code, name: region.name, industry, label };
}

// 화면을 보고 다음 클릭까지 쉬는 시간(초). 빼면 VU 10명이 사람 수백 명처럼 때린다.
export const think = (min, max) => min + Math.random() * (max - min);

// 지원사업 검색·분석 질문 (2차, 임베딩 경로) — 사용자가 적을 법한 표현. 관련 공고가 있는 것·없는 것을 섞었다.
export const SEARCH_QUERIES = [
  '인테리어 비용', '청년 창업 대출', '폐업 후 재창업', '임대료 부담', '온라인 판로 마케팅', '고용보험료 지원',
  '카페 창업 자금', '수출 해외 진출', '정책자금 융자', '배달 앱 수수료', '간판 교체', '직원 인건비',
  '상권 분석 컨설팅', '재난 피해 지원', '전기요금 부담', '디지털 전환 교육',
];
export const pickQuery = () => SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
// 임베딩을 쓰는 비율(가정, 실측 아님): 지원사업 방문의 절반이 검색, 분석의 절반이 질문 포함
export const EMBED_SHARE = 0.5;
