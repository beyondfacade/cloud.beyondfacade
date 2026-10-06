import { expect, it } from "vitest";
import { GET } from "./route";

function call(regionCode: string, query = "?industry=korean_food") {
  return GET(new Request(`http://test/api/mock/verdicts/${regionCode}${query}`), {
    params: Promise.resolve({ regionCode }),
  });
}

it("단건은 판정 원천 basis를 싣는다 — 인허가 업종은 permit", async () => {
  const res = await call("1168064000");
  expect(res.status).toBe(200);
  const v = await res.json();
  expect(v.basis).toBe("permit");
  for (const signal of v.signals) {
    if (signal.percentile === null) {
      expect(signal.band).toBeNull();
      expect(signal.band_label).toBeNull();
    } else {
      expect(["very_bad", "bad", "normal", "good", "very_good"]).toContain(signal.band);
      expect(signal.band_label).toEqual(expect.any(String));
      expect(signal.evidence).toContain(` — ${signal.band_label}(서울 한식 동을 100곳으로 치면 `);
      expect(signal.evidence).not.toMatch(/상위|하위/);
    }
  }
});

it("편의점은 판정 대상이 아니라 404 INDUSTRY_NOT_FOUND", async () => {
  const res = await call("1168064000", "?industry=convenience_store");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});

it("부동산은 판정 대상이 아니라 404 INDUSTRY_NOT_FOUND", async () => {
  const res = await call("1168064000", "?industry=real_estate");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});

it("단건은 신호 4개 중 판정 가능 신호가 한 개이면 보류한다", async () => {
  const res = await call("1135056000", "?industry=chinese_food"); // 월계1동
  expect(res.status).toBe(200);
  const v = await res.json();
  expect(v.signals.map((s: { key: string }) => s.key)).toEqual(["net_outflow", "survival_cliff", "early_closure", "saturation"]);
  expect(v.signals.map((s: { level: string }) => s.level)).toEqual([
    "unavailable", "unavailable", "unavailable", "off",
  ]);
  expect(v).toMatchObject({ verdict_code: "insufficient", strong_count: 0, on_count: 0 });
  for (const s of v.signals) expect(s.evidence.length).toBeGreaterThan(5);
});

it("목록 라우트와 같은 판정 코드를 준다 (두 계약의 원천이 하나)", async () => {
  const { GET: list } = await import("../route");
  const rows = await (await list(new Request("http://test/api/mock/verdicts?industry=korean_food"))).json();
  const row = rows.find((r: { region_code: string }) => r.region_code === "1168064000");
  expect((await (await call("1168064000")).json()).verdict_code).toBe(row.value);
});

it("모르는 동은 404 VERDICT_NOT_FOUND, 판정 대상이 아닌 업종은 404 INDUSTRY_NOT_FOUND", async () => {
  const missing = await call("0000000000");
  expect(missing.status).toBe(404);
  expect((await missing.json()).error.code).toBe("VERDICT_NOT_FOUND");
  const academy = await call("1168064000", "?industry=academy");
  expect((await academy.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});
