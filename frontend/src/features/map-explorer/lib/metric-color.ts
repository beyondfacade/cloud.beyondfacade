export type ColorScheme = "sequential" | "diverging";

/** 색약 안전 팔레트 (ColorBrewer 7클래스). 데이터 시각화 전용 상수 — UI 토큰과 별개 체계.
 *  연속 보간 대신 이산 클래스 — 인접 region의 색 대비를 키워 단계구분도 판독성을 높인다. */
const SEQUENTIAL_CLASSES = ["#ffffb2", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#b10026"]; // YlOrRd
const DIVERGING_CLASSES = ["#2166ac", "#4393c3", "#92c5de", "#f7f7f7", "#f4a582", "#d6604d", "#b2182b"]; // RdBu 역순

/** 값이 없는 region의 fill-color, 그리고 안전 폴백으로 재사용하는 중립 회색. */
export const NO_DATA_COLOR = "#cccccc";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** 선형 보간 분위수 — sorted에서 p(0~1) 위치의 값. */
function quantile(sorted: number[], p: number): number {
  const pos = p * (sorted.length - 1);
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

/** sequential: 분위수 경계 — 각 클래스에 비슷한 개수의 region이 들어가 색 대비가 최대화된다. */
function sequentialScale(values: number[]): (value: number) => string {
  const sorted = [...values].sort((a, b) => a - b);
  const k = SEQUENTIAL_CLASSES.length;
  const breaks = Array.from({ length: k - 1 }, (_, i) => quantile(sorted, (i + 1) / k));
  return (value) => SEQUENTIAL_CLASSES[breaks.filter((b) => b <= value).length];
}

/** diverging: 0 중심 대칭 — 음수는 파랑, 0 부근은 중립, 양수는 빨강 (성장률 부호가 그대로 색 부호). */
function divergingScale(values: number[]): (value: number) => string {
  const extent = Math.max(...values.map(Math.abs)) || 1;
  const k = DIVERGING_CLASSES.length;
  return (value) => {
    const t = clamp(value / extent, -1, 1);
    return DIVERGING_CLASSES[Math.min(Math.floor(((t + 1) / 2) * k), k - 1)];
  };
}

/** 값 분포로부터 region 색상 함수를 만든다. 값이 없으면 항상 NO_DATA_COLOR. */
export function makeMetricColorScale(values: number[], scheme: ColorScheme): (value: number) => string {
  if (values.length === 0) return () => NO_DATA_COLOR;
  return scheme === "sequential" ? sequentialScale(values) : divergingScale(values);
}
