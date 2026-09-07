export type ColorScheme = "sequential" | "diverging";

/** 색약 안전 팔레트 (ColorBrewer 7클래스). 데이터 시각화 전용 상수 — UI 토큰과 별개 체계.
 *  연속 보간 대신 이산 클래스 — 인접 region의 색 대비를 키워 단계구분도 판독성을 높인다. */
const SEQUENTIAL_CLASSES = ["#ffffb2", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#b10026"]; // YlOrRd
const DIVERGING_CLASSES = ["#2166ac", "#4393c3", "#92c5de", "#f7f7f7", "#f4a582", "#d6604d", "#b2182b"]; // RdBu 역순

/** 값이 없는 region의 fill-color, 그리고 안전 폴백으로 재사용하는 중립 회색. */
export const NO_DATA_COLOR = "#cccccc";

/** 단계구분도 한 클래스 — 색과 값 구간 [from, to]. 범례가 그대로 소비한다. */
export interface MetricColorClass {
  color: string;
  from: number;
  to: number;
}

export interface MetricColorScale {
  colorOf: (value: number) => string;
  classes: MetricColorClass[];
}

/** 선형 보간 분위수 — sorted에서 p(0~1) 위치의 값. */
function quantile(sorted: number[], p: number): number {
  const pos = p * (sorted.length - 1);
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

/** 내부 경계 breaks(k-1개)와 도메인 양끝으로 colorOf·classes를 함께 만든다 — 경계 계산의 단일 원천.
 *  경계값은 위 클래스에 속한다([from, to) 방향). 도메인 밖 값은 양끝 클래스로 자연 클램프된다. */
function scaleFromBreaks(palette: string[], breaks: number[], min: number, max: number): MetricColorScale {
  const edges = [min, ...breaks, max];
  return {
    colorOf: (value) => palette[breaks.filter((b) => b <= value).length],
    classes: palette.map((color, i) => ({ color, from: edges[i], to: edges[i + 1] })),
  };
}

/** sequential: 분위수 경계 — 각 클래스에 비슷한 개수의 region이 들어가 색 대비가 최대화된다. */
function sequentialScale(values: number[]): MetricColorScale {
  const sorted = [...values].sort((a, b) => a - b);
  const k = SEQUENTIAL_CLASSES.length;
  const breaks = Array.from({ length: k - 1 }, (_, i) => quantile(sorted, (i + 1) / k));
  return scaleFromBreaks(SEQUENTIAL_CLASSES, breaks, sorted[0], sorted[sorted.length - 1]);
}

/** diverging: 0 중심 대칭 — 음수는 파랑, 0 부근은 중립, 양수는 빨강 (성장률 부호가 그대로 색 부호). */
function divergingScale(values: number[]): MetricColorScale {
  const extent = Math.max(...values.map(Math.abs)) || 1;
  const k = DIVERGING_CLASSES.length;
  const breaks = Array.from({ length: k - 1 }, (_, i) => -extent + ((i + 1) * 2 * extent) / k);
  return scaleFromBreaks(DIVERGING_CLASSES, breaks, -extent, extent);
}

/** 값 분포로부터 region 색상 함수와 범례용 클래스 경계를 만든다. 값이 없으면 항상 NO_DATA_COLOR + 빈 classes. */
export function makeMetricColorScale(values: number[], scheme: ColorScheme): MetricColorScale {
  if (values.length === 0) return { colorOf: () => NO_DATA_COLOR, classes: [] };
  return scheme === "sequential" ? sequentialScale(values) : divergingScale(values);
}
