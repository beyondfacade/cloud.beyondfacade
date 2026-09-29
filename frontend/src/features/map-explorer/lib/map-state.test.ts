import { expect, it } from "vitest";
import { parseMapState, serializeMapState, SNAPSHOT_INDUSTRIES } from "./map-state";

it("파라미터가 없으면 업종·동·예산의 기본값을 반환한다", () => {
  expect(parseMapState(new URLSearchParams())).toEqual({ industry: "cafe", region: null, budget: null });
});

it("업종·동·예산만 직렬화하고 왕복해서 보존한다", () => {
  const state = { industry: "karaoke", region: "1168051500", budget: 50_000_000 };
  const query = serializeMapState(state);
  expect(query).toBe("industry=karaoke&region=1168051500&budget=50000000");
  expect(parseMapState(new URLSearchParams(query))).toEqual(state);
});

it.each([
  "metric=closure_rate&year=2021&year_quarter=20244",
  "metric=verdict&year=2026&year_quarter=20262",
  "metric=unknown&year=bad&year_quarter=bad",
])("옛 파라미터 %s를 무시하고 동·업종·예산을 유지한다", (legacy) => {
  expect(parseMapState(new URLSearchParams(`industry=korean_food&region=1168064000&budget=50000000&${legacy}`)))
    .toEqual({ industry: "korean_food", region: "1168064000", budget: 50_000_000 });
});

it("업종을 바꿔도 관문에서 온 예산은 URL에 남는다", () => {
  const landed = parseMapState(new URLSearchParams("region=1168064000&industry=cafe&budget=50000000"));
  const changed = new URLSearchParams(serializeMapState({ ...landed, industry: "karaoke" }));
  expect(changed.get("budget")).toBe("50000000");
});

it.each(["abc", "0", "-1", "1.5"])("유효하지 않은 예산 %s는 버린다", (budget) => {
  expect(parseMapState(new URLSearchParams({ budget })).budget).toBeNull();
});

it("알 수 없는 업종은 기본값으로 바꾼다", () => {
  expect(parseMapState(new URLSearchParams("industry=hack")).industry).toBe("cafe");
});

it("동과 예산이 없으면 URL에서 생략한다", () => {
  expect(serializeMapState({ industry: "cafe", region: null, budget: null })).toBe("industry=cafe");
});

it("스냅샷 업종에는 어린이집·편의점이 포함된다", () => {
  expect(SNAPSHOT_INDUSTRIES.has("childcare")).toBe(true);
  expect(SNAPSHOT_INDUSTRIES.has("convenience_store")).toBe(true);
});
