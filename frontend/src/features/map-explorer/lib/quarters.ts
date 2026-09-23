/** 분기 어휘 — 동×분기 지표의 시간 축. 문자열은 백엔드 계약 그대로 `'20262'`(연 4자리 + 분기 1자리).
 *
 *  범위는 백엔드 적재 범위와 같다: neighborhood·profile 20211~20262(22분기). commerce(매출) 계열은
 *  20254까지라 그 지표는 마지막 두 분기가 빈 지도로 뜬다 — 백엔드가 "값 없는 동은 행을 만들지 않는다"
 *  계약이라 색만 안 칠해진다. 최신 분기를 여기 상수로 두는 것은 화면이 "최신"이 언제인지 몰라서가
 *  아니라(백엔드가 분기 생략 시 고른다) 셀렉터 목록을 그리기 위해서다. 적재가 늘면 이 상수만 올린다. */
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
