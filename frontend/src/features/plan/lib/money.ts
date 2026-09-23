/** 폼 입력 UX용 원↔만원 변환. 내부 상태(FinanceInput)는 항상 원 단위 정수다. 대구 `simulator/lib/money.ts` 이식. */

const WON_PER_MANWON = 10_000;

export function wonToManwon(won: number): number {
  return Math.round(won / WON_PER_MANWON);
}

export function manwonToWon(manwon: number): number {
  return manwon * WON_PER_MANWON;
}

/** 화면 표기 — "3,160만 원". 음수는 부호를 살린다(영업이익). */
export function formatManwon(won: number): string {
  const manwon = wonToManwon(Math.abs(won));
  return `${won < 0 ? "−" : ""}${manwon.toLocaleString("ko-KR")}만 원`;
}

/** 비율 → "4.05%" (소수 2자리까지, 뒤 0 제거). */
export function formatPercent(ratio: number): string {
  return `${Number((ratio * 100).toFixed(2))}%`;
}
