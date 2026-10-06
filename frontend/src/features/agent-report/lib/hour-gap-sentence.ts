import type { HourGapBand } from "@/shared/api/types";
import { hourBandLabel } from "./neighborhood-charts";

/** 강도가 가장 큰 구간. 동점은 앞 구간(원천 순서). 값이 없으면 null. */
function peakBand(bands: HourGapBand[], pick: (b: HourGapBand) => number): string | null {
  let best: HourGapBand | null = null;
  for (const band of bands) if (best === null || pick(band) > pick(best)) best = band;
  return best?.hour_band ?? null;
}

/** 어긋남 문장 — 결정론. gap의 부호가 아니라 두 최대 구간의 위치로 말한다(무대 설계서 §6-2).
 *  관문 `diagnosis`와 같은 어휘("점심(11~14시)")를 쓴다. */
export function hourGapSentence(bands: HourGapBand[]): string | null {
  const people = peakBand(bands, (b) => b.footfall_intensity);
  const money = peakBand(bands, (b) => b.sales_intensity);
  if (!people || !money) return null;
  if (people === money) return `사람(유동인구)과 매출이 모두 ${hourBandLabel(people)}에 가장 많습니다.`;
  return `사람(유동인구)이 가장 많은 때는 ${hourBandLabel(people)}입니다. 매출이 가장 많은 때는 ${hourBandLabel(money)}으로, 사람이 가장 많은 때와 다릅니다.`;
}
