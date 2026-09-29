import type { UnavailableFact } from "@/shared/api/types";

/** 항목별 조회 실패와 이전/부분 응답의 누락을 같은 결측으로 처리한다. */
export function availableFact<T>(fact: T | UnavailableFact | null | undefined): T | undefined {
  if (fact == null || (typeof fact === "object" && "available" in fact && fact.available === false)) return undefined;
  return fact as T;
}
