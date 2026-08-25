export type ColorScheme = "sequential" | "diverging";

type Rgb = [number, number, number];

/** 색약 안전 팔레트 (ColorBrewer 계열). 데이터 시각화 전용 상수 — UI 토큰과 별개 체계. */
const SEQUENTIAL_STOPS = ["#fee8c8", "#fdbb84", "#fc8d59", "#e34a33", "#7f0000"];
const DIVERGING_STOPS = ["#2166ac", "#67a9cf", "#f7f7f7", "#ef8a62", "#b2182b"];

/** 값이 없는 region의 fill-color, 그리고 안전 폴백으로 재사용하는 중립 회색. */
export const NO_DATA_COLOR = "#cccccc";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function hexToRgb(hex: string): Rgb {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex([r, g, b]: Rgb): string {
  const toHex = (v: number) => Math.round(v).toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** value를 domain 안에서 0~1로 정규화한 뒤, 팔레트 스톱 사이를 RGB 선형 보간한다. */
export function metricColor(value: number, domain: [number, number], scheme: ColorScheme): string {
  const [min, max] = domain;
  const t = max === min ? 0 : clamp((value - min) / (max - min), 0, 1);

  const stops = scheme === "sequential" ? SEQUENTIAL_STOPS : DIVERGING_STOPS;
  const segments = stops.length - 1;
  const scaled = t * segments;
  const index = Math.min(Math.floor(scaled), segments - 1);
  const localT = scaled - index;

  const from = hexToRgb(stops[index]);
  const to = hexToRgb(stops[index + 1]);
  const rgb: Rgb = [lerp(from[0], to[0], localT), lerp(from[1], to[1], localT), lerp(from[2], to[2], localT)];

  return rgbToHex(rgb);
}
