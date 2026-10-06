/** 동네 유형·시간대 라벨의 표기 어휘. 코드는 API 계약 값이므로 영문을 유지하고 화면에는 라벨만 노출한다.
 *  판정 자체는 백엔드(파생 지표 배치)가 하고, 여기는 그 코드를 사람이 읽는 말로 옮기기만 한다.
 *  지도 탐색·AI 분석 두 feature가 함께 쓸 공통 어휘이므로 shared에 둔다 (feature 간 직접 import 금지). */

export const NEIGHBORHOOD_TYPES = [
  "office",
  "campus",
  "dining",
  "hub",
  "residential",
  "mixed",
] as const;

export type NeighborhoodType = (typeof NEIGHBORHOOD_TYPES)[number];

export interface NeighborhoodTypeLabel {
  /** 화면에 띄우는 이름. */
  name: string;
  /** 이름 옆에 항상 붙는 괄호 설명 — 이름만으로 뜻이 안 서는 유형이 있다. */
  qualifier: string;
  /** 마우스를 올리거나 터치했을 때 뜨는 한 문장. */
  tooltip: string;
}

const LABELS: Record<NeighborhoodType, NeighborhoodTypeLabel> = {
  // `업무 밀집형`으로 두면 가회동(북촌)·한남동·청담동·압구정동처럼 오피스가 아닌 동에 붙어
  // 틀린 말이 된다. 이 유형이 실제로 잡아내는 것은 "상주 대비 낮 인구가 압도적인 동"이다
  office: {
    name: "낮 인구 우위형",
    qualifier: "낮에 사람이 몰리는 곳",
    tooltip: "직장인구가 상주인구보다 훨씬 많고 주말에 비는 동네입니다.",
  },
  campus: {
    name: "대학가형",
    qualifier: "대학 상권",
    tooltip: "대학이 있고 거리의 20대 비중이 서울 상위권인 동네입니다.",
  },
  dining: {
    name: "먹자·나들이형",
    qualifier: "외식 상권",
    tooltip: "음식·유흥 결제가 서울 상위권인 동네입니다.",
  },
  hub: {
    name: "생활 중심형",
    qualifier: "동네 거점",
    tooltip: "사람도 많고 생활 시설도 많은 지역 거점입니다.",
  },
  residential: {
    name: "주거형",
    qualifier: "주택가",
    tooltip: "사람이 살고 밤에 머무는 동네입니다. 외부 유입보다 동네 수요가 중심입니다.",
  },
  mixed: {
    name: "혼합형",
    qualifier: "뚜렷한 특징 없음",
    tooltip:
      "어느 지표도 서울 동 가운데 두드러지게 높거나 낮지 않은 동네입니다. 대단지 아파트가 동 전체를 차지한 곳이 많습니다.",
  },
};

/** 알 수 없는 코드는 원문을 이름으로 돌려준다 — 백엔드가 유형을 늘려도 화면이 빈 칸으로 깨지지 않는다. */
export function neighborhoodTypeLabel(code: string): NeighborhoodTypeLabel {
  return LABELS[code as NeighborhoodType] ?? { name: code, qualifier: "분류 없음", tooltip: "" };
}

/** 시간대 라벨 5종. `flat`은 정점이 뚜렷하지 않은 동네다 (평탄도 하위 25%). */
const TIME_LABEL_SENTENCES: Record<string, string> = {
  night: "낮엔 조용하고 밤에 채워지는 동네",
  flat: "하루 종일 사람이 고르게 있는 동네",
  day: "점심·오후가 하루의 정점",
  evening: "퇴근 시간부터가 진짜",
  morning: "출근길에만 붐비는 동네",
};

export function timeLabelSentence(label: string | null): string | null {
  return label === null ? null : (TIME_LABEL_SENTENCES[label] ?? null);
}
