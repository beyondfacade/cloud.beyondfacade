/** 분기 어휘 — 동×분기 지표의 시간 축. 문자열은 백엔드 계약 그대로 `'20262'`(연 4자리 + 분기 1자리).
 *
 *  범위는 백엔드 적재 범위와 같다 — 20211~20262(22분기). **동네 지표 4종 모두 전 22분기가 422행씩
 *  빠짐없이 차 있다**(2026-09-24 실DB·실 API 실측). 20254까지인 것은 매출·점포·시간대 어긋남
 *  테이블인데, 그쪽은 단계구분도가 아니라 사이드패널 차트가 쓰고 이미 404 + 안내로 처리된다.
 *  지표마다 범위가 갈리면 `metric-coverage.ts`의 `availableQuarters`에서 나눈다 — 셀렉터는 그 함수만 본다.
 *  최신 분기를 여기 상수로 두는 것은 화면이 "최신"이 언제인지 몰라서가 아니라(백엔드가 분기 생략 시
 *  고른다) 셀렉터 목록을 그리기 위해서다. 적재가 늘면 이 상수만 올린다. */
export const FIRST_QUARTER = "20211";
export const LATEST_QUARTER = "20262";

const QUARTER_RE = /^\d{4}[1-4]$/;

export function isQuarter(value: string | null | undefined): value is string {
  return typeof value === "string" && QUARTER_RE.test(value);
}

function nextQuarter(yq: string): string {
  const year = Number(yq.slice(0, 4));
  const q = Number(yq[4]);
  return q === 4 ? `${year + 1}1` : `${year}${q + 1}`;
}

/** FIRST_QUARTER~LATEST_QUARTER 오름차순 목록 (셀렉터 옵션). */
export function listQuarters(first = FIRST_QUARTER, latest = LATEST_QUARTER): string[] {
  const out: string[] = [];
  for (let yq = first; yq <= latest; yq = nextQuarter(yq)) out.push(yq);
  return out;
}

export const QUARTERS = listQuarters();

/** '20262' → '2026년 2분기'. */
export function formatQuarter(yq: string): string {
  return `${yq.slice(0, 4)}년 ${yq[4]}분기`;
}
