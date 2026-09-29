/** 값이 없는 동의 중립 회색 — 데이터 시각화 전용 상수. */
export const NO_DATA_COLOR = "#cccccc";

/** 범주 단계구분도 한 클래스 — 색과 코드. 범례가 이름으로 바꿔 띄운다(코드→이름은 판정 원천). */
export interface CategoryColorClass {
  color: string;
  code: string;
}

export interface CategoryColorScale {
  colorOf: (code: string) => string;
  classes: CategoryColorClass[];
}

/** 범주 스케일 — 코드에 대응하는 색과 범례를 함께 만든다.
 *  colorOf와 classes가 같은 palette 객체를 공유해 지도 색과 범례 색이 어긋나지 않는다.
 *  classes는 `order` 순의 전체 키다 — 범주 범례는 구간이 아니라 키(key)라 데이터에 없는 유형도 보인다.
 *  코드가 하나도 없으면(데이터 없음) 빈 classes — 범례가 숨는다. */
export function makeCategoryColorScale(
  codes: string[],
  palette: Record<string, string>,
  order: readonly string[],
): CategoryColorScale {
  if (codes.length === 0) return { colorOf: () => NO_DATA_COLOR, classes: [] };
  return {
    colorOf: (code) => palette[code] ?? NO_DATA_COLOR,
    classes: order.map((code) => ({ code, color: palette[code] ?? NO_DATA_COLOR })),
  };
}
