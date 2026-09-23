/** 현재 테마의 --accent CSS 토큰을 읽는다. maplibre paint는 CSS var()를 모르므로 계산값을 넘긴다. */
export function readAccentColor(fallback = "#cccccc"): string {
  if (typeof document === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || fallback;
}
