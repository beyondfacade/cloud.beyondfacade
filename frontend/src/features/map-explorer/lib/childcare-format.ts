/** 어린이집 수치 표기 — 사이드패널·마커 팝업 공용 순수 함수. */

export function formatOccupancy(rate: number | null): string {
  return rate === null ? "—" : `${(rate * 100).toFixed(1)}%`;
}

/** 원천 공란(null)은 0이 아니라 미공개 — 0으로 추정하지 않는다 (백엔드 계약과 동일). */
export function formatWaiting(count: number | null): string {
  return count === null ? "미공개" : `${count.toLocaleString("ko-KR")}건`;
}
