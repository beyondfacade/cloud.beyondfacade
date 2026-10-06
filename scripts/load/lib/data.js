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
