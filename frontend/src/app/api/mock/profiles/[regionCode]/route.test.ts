import { expect, it } from "vitest";
import { GET } from "./route";
import { NEIGHBORHOOD_TYPES } from "@/shared/neighborhood";

const KNOWN = "1168064000";

function call(regionCode: string, query = "") {
  return GET(new Request(`http://test/api/mock/profiles/${regionCode}${query}`), {
    params: Promise.resolve({ regionCode }),
  });
}

it("분기를 생략하면 200과 최신 분기 프로필을 반환한다", async () => {
  const res = await call(KNOWN);
  expect(res.status).toBe(200);
  const profile = await res.json();
  expect(profile.region_code).toBe(KNOWN);
  expect(profile.year_quarter).toBe("20262");
  expect(NEIGHBORHOOD_TYPES).toContain(profile.neighborhood_type);
  expect(profile.type_reason).not.toBe("");
});

it("분기를 지정하면 그 분기를 반환한다", async () => {
  const profile = await (await call(KNOWN, "?year_quarter=20251")).json();
  expect(profile.year_quarter).toBe("20251");
});

it("같은 입력은 항상 같은 값을 준다 (Math.random 금지 계약)", async () => {
  const first = await (await call(KNOWN)).json();
  const second = await (await call(KNOWN)).json();
  expect(first).toEqual(second);
});

it("시간대 라벨과 정점·바닥은 실 API의 어휘를 쓴다", async () => {
  const profile = await (await call(KNOWN)).json();
  expect(["morning", "day", "evening", "night", "flat", null]).toContain(profile.time_label);
  expect(["morning", "day", "evening", "night", null]).toContain(profile.peak_block);
  expect(["morning", "day", "evening", "night", null]).toContain(profile.trough_block);
});

it("알 수 없는 동은 404 REGION_PROFILE_NOT_FOUND를 반환한다", async () => {
  const res = await call("9999999999");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("REGION_PROFILE_NOT_FOUND");
});

it("형식이 틀린 분기도 500이 아니라 404다", async () => {
  const res = await call(KNOWN, "?year_quarter=2026");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("REGION_PROFILE_NOT_FOUND");
});
