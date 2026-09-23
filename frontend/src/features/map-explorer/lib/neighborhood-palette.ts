/** 동네 유형 6종의 범주 팔레트 — 데이터 시각화 전용 상수. tokens.css의 UI 토큰 체계와 분리된 별도 체계다
 *  (tokens.css 상단 선언과 같은 원칙; metric-color.ts의 분위수 팔레트도 같은 편에 있다).
 *
 *  원칙 — 주거형이 422동 중 60%라 지도를 지배한다. 주거형을 **가장 옅게**(지도 배경에 가장 가깝게) 두고
 *  나머지 5종이 튀게 한다. "옅다"는 명도로 정의한다: 라이트 테마에서는 배경이 밝으니 가장 밝은 색,
 *  다크 테마에서는 배경이 어두우니 가장 어두운 색이다. 6색은 색상뿐 아니라 명도 차로도 갈리게 골라
 *  색맹에서도 구분되게 하되, 6종은 색만으로는 못 가르므로 범례가 필수다. */
import type { NeighborhoodType } from "@/shared/neighborhood";

export type MapTheme = "light" | "dark";

const LIGHT: Record<NeighborhoodType, string> = {
  office: "#3b6fb6", // 파랑 — 낮 인구 우위
  campus: "#7b4fb0", // 보라 — 대학가
  dining: "#e0642e", // 주황 — 먹자·나들이
  hub: "#2a9d8f", // 청록 — 생활 중심
  residential: "#d9d4c7", // 가장 옅은 베이지 — 주거 (60%)
  mixed: "#8a8f99", // 중간 회색 — 특징 없음
};

const DARK: Record<NeighborhoodType, string> = {
  office: "#6ea0e6",
  campus: "#b48ae6",
  dining: "#f2915a",
  hub: "#5cc8b8",
  residential: "#3d4250", // 가장 어두운 — 밤 타일에 가장 가깝다
  mixed: "#9aa0aa",
};

export const NEIGHBORHOOD_PALETTES: Record<MapTheme, Record<NeighborhoodType, string>> = {
  light: LIGHT,
  dark: DARK,
};

export function neighborhoodPalette(theme: MapTheme): Record<NeighborhoodType, string> {
  return NEIGHBORHOOD_PALETTES[theme];
}

/** WCAG 상대 명도 (0 검정 ~ 1 흰색). 팔레트 원칙("주거형이 가장 옅다")을 테스트로 고정하는 데 쓴다. */
export function relativeLuminance(hex: string): number {
  const channel = (index: number) => {
    const c = parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2);
}
