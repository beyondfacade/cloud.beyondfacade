/** 판정 4범주의 지도 팔레트 — 데이터 시각화 전용 상수. tokens.css의 UI 토큰과 분리된 별도 체계다
 *  카드·배지의 색은 토큰(--danger·--warn)을 쓰고, 여기 값은 WebGL fill과 지도 범례에 쓴다.
 *  원칙 — 경고 없음·보류가 가장 옅고(배경에 가깝게) 빨강·주황이 튄다. 옅음은 명도로 정의한다. */
import type { VerdictCode } from "@/shared/api/types";
export type MapTheme = "light" | "dark";

const LIGHT: Record<VerdictCode, string> = {
  red: "#c8102e",
  orange: "#e8862a",
  clear: "#dcdad3", // 가장 옅은 회베이지
  insufficient: "#ecebe7", // 보류 — clear보다 더 옅게, 빗금 대신 명도로 구분
};

const DARK: Record<VerdictCode, string> = {
  red: "#ff5a6a",
  orange: "#ffa64d",
  clear: "#3a3f4b", // 밤 타일에 가장 가깝다
  insufficient: "#2c303a",
};

export function verdictPalette(theme: MapTheme): Record<VerdictCode, string> {
  return theme === "dark" ? DARK : LIGHT;
}
