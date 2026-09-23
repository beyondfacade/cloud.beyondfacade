import { expect, it } from "vitest";
import { GET } from "./route";

function call(query: string) {
  return GET(new Request(`http://test/api/mock/profiles${query}`));
}

it("지원 metric은 200과 region_code·value 쌍 목록을 반환한다", async () => {
  const res = await call("?metric=night_index");
  expect(res.status).toBe(200);
  const rows = await res.json();
  expect(rows.length).toBeGreaterThan(400);
  expect(Object.keys(rows[0]).sort()).toEqual(["region_code", "value"]);
});

it("업종을 넘겨도 값이 달라지지 않는다 (동 단위 지표 계약)", async () => {
  const a = await (await call("?metric=fnb_share&industry=cafe")).json();
  const b = await (await call("?metric=fnb_share")).json();
  expect(a).toEqual(b);
});

it("분기를 생략하면 최신 분기와 같고, 다른 분기는 값이 달라진다", async () => {
  const latest = await (await call("?metric=night_index")).json();
  const pinned = await (await call("?metric=night_index&year_quarter=20262")).json();
  const older = await (await call("?metric=night_index&year_quarter=20251")).json();
  expect(latest).toEqual(pinned);
  expect(older).not.toEqual(latest);
});

it("단일 프로필 라우트와 같은 값을 준다 (두 계약의 원천이 하나)", async () => {
  const { GET: single } = await import("./[regionCode]/route");
  const rows = await (await call("?metric=night_index")).json();
  const first = rows[0];
  const profile = await (
    await single(new Request(`http://test/api/mock/profiles/${first.region_code}`), {
      params: Promise.resolve({ regionCode: first.region_code }),
    })
  ).json();
  expect(profile.night_index).toBe(first.value);
});

it("미지원 metric은 500이 아니라 404 METRIC_NOT_FOUND다", async () => {
  const res = await call("?metric=type_reason");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("METRIC_NOT_FOUND");
});
