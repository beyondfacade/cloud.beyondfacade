/** 정점→바닥 쌍의 서사. 관측이 많은 5종만 둔다 — 나머지 4종은 전 서울에 7개 동뿐이라
 *  문장을 만들면 한두 동의 잡음이 단정으로 굳는다. 없으면 화면이 시간대 라벨 문장으로 대체한다. */
const PHASES_NARRATIVES: Record<string, string> = {
  "night>day": "낮에는 거리가 비고, 밤이 되어서야 사람이 돌아옵니다",
  "day>night": "점심·오후에 정점을 찍고, 밤이면 텅 빕니다",
  "evening>morning": "아침은 늦게 열리고, 저녁이 가장 붐빕니다",
  "evening>night": "저녁에 몰렸다가 밤에는 빠져나갑니다",
  "night>evening": "저녁에 잠깐 비었다가 밤에 다시 채워집니다",
};

export function phasesNarrative(peak: string | null, trough: string | null): string | null {
  if (!peak || !trough) return null;
  return PHASES_NARRATIVES[`${peak}>${trough}`] ?? null;
}

/** 시간대 6구간 — 원천 순서. 표기는 백엔드 intent BC `neighborhood_vocabulary.py`와 같다(관문 진단 문장과 어긋나지 않게). */
export const HOUR_BANDS = ["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"] as const;

export const HOUR_BAND_LABELS: Record<(typeof HOUR_BANDS)[number], string> = {
  "00_06": "새벽(00~06시)",
  "06_11": "아침(06~11시)",
  "11_14": "점심(11~14시)",
  "14_17": "오후(14~17시)",
  "17_21": "저녁(17~21시)",
  "21_24": "밤(21~24시)",
};

export function hourBandLabel(band: string): string {
  return HOUR_BAND_LABELS[band as (typeof HOUR_BANDS)[number]] ?? band;
}

/** 4블록 — 6구간을 아침·낮·저녁·밤으로 묶은 것. 밤이 21~24와 00~06을 합친다. */
export const TIME_BLOCKS = ["morning", "day", "evening", "night"] as const;

export const TIME_BLOCK_LABELS: Record<(typeof TIME_BLOCKS)[number], string> = {
  morning: "아침",
  day: "낮",
  evening: "저녁",
  night: "밤",
};
