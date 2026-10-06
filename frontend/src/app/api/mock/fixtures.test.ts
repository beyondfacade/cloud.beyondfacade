import { expect, it } from "vitest";
import { SEOUL_REGIONS_GEOJSON, metricRows, summaryOf, agentEventScript, verdictOf } from "./fixtures";

it.each([
  ["korean_food", "net_outflow", "normal", "순유출 보통", "많은", 28],
  ["korean_food", "survival_cliff", "good", "생존율 높은 편", "낮은", 85],
  ["korean_food", "early_closure", "very_good", "폐업 점포 영업 기간 매우 긴 편", "짧은", 98],
  ["real_estate", "saturation", "very_bad", "밀집 매우 높은 편", "높은", 7],
  ["real_estate", "closure_rate", "bad", "폐업률 높은 편", "높은", 20],
  ["convenience_store", "tobacco_gap", "very_good", "담배소매인 반경 안 상가 비율 매우 낮은 편", "높은", 91],
  ["real_estate", "trade_per_office", "normal", "사무소당 거래 보통", "적은", 50],
])("%s의 %s 신호는 위험 등급과 방향을 설명한 순위를 결정적으로 제공한다", (industry, key, band, band_label, direction, rank) => {
  const verdict = verdictOf("1168064000", industry as string);
  const signal = verdict.signals.find((s) => s.key === key)!;
  expect(signal).toMatchObject({ band, band_label });
  expect(signal.evidence).toContain(` — ${band_label}(서울 `);
  expect(signal.evidence).toContain(` 동을 100곳으로 치면 ${direction} 쪽에서 ${rank}번째쯤)`);
  expect(signal.evidence).not.toMatch(/상위|하위/);
  expect(verdictOf("1168064000", industry as string)).toEqual(verdict);
});

it("geojson feature마다 region_code·name이 있다", () => {
  expect(SEOUL_REGIONS_GEOJSON.features.length).toBeGreaterThanOrEqual(8);
  for (const f of SEOUL_REGIONS_GEOJSON.features)
    expect(f.properties).toMatchObject({ region_code: expect.any(String), name: expect.any(String) });
});
it("metricRows는 모든 feature의 region_code를 커버한다", () => {
  const codes = new Set(metricRows("closure_rate", 2026, "cafe").map((r) => r.region_code));
  for (const f of SEOUL_REGIONS_GEOJSON.features) expect(codes.has(f.properties!.region_code)).toBe(true);
});
it("metricRows는 industry가 다르면 값도 달라진다", () => {
  expect(metricRows("closure_rate", 2026, "cafe")).not.toEqual(metricRows("closure_rate", 2026, "gym"));
});
it("metricRows는 같은 (metric, year, industry)에 대해 결정적이다", () => {
  expect(metricRows("closure_rate", 2026, "cafe")).toEqual(metricRows("closure_rate", 2026, "cafe"));
});
it("summaryOf는 industry가 다르면 점포수·폐업률·성장률 카드 값도 달라진다", () => {
  const code = SEOUL_REGIONS_GEOJSON.features[0].properties!.region_code;
  const cafeCards = summaryOf(code, "cafe").cards.filter((c) => c.grade === "fact");
  const gymCards = summaryOf(code, "gym").cards.filter((c) => c.grade === "fact");
  expect(cafeCards).not.toEqual(gymCards);
});
it("이벤트 스크립트는 report_done으로 끝난다", () => {
  const script = agentEventScript();
  expect(script.at(-1)!.type).toBe("report_done");
});

it("네 판정 신호가 모두 꺼진 동은 경고 없음이다", () => {
  const verdict = verdictOf("1121582000", "cafe"); // 자양제1동
  expect(verdict.signals.map(({ key, level }) => ({ key, level }))).toEqual([
    { key: "net_outflow", level: "off" },
    { key: "survival_cliff", level: "off" },
    { key: "early_closure", level: "off" },
    { key: "saturation", level: "off" },
  ]);
  expect(verdict).toMatchObject({ verdict_code: "clear", strong_count: 0, on_count: 0 });
});

it("판정 가능한 신호가 두 개이면 판정을 보류하지 않는다", () => {
  const verdict = verdictOf("1117052000", "cafe"); // 용산2가동
  expect(verdict.signals.map(({ level }) => level)).toEqual([
    "unavailable", "unavailable", "off", "off",
  ]);
  expect(verdict.verdict_code).toBe("clear");
});
