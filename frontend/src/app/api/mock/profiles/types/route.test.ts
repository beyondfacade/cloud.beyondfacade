import { expect, it } from "vitest";
import { NEIGHBORHOOD_TYPES } from "@/shared/neighborhood";
import { GET } from "./route";

function call(query = "") {
  return GET(new Request(`http://test/api/mock/profiles/types${query}`));
}

it("전 행정동의 {region_code, type_code} 쌍을 반환한다", async () => {
  const res = await call();
  expect(res.status).toBe(200);
  const rows = await res.json();
  expect(rows.length).toBeGreaterThan(400);
  expect(Object.keys(rows[0]).sort()).toEqual(["region_code", "type_code"]);
  for (const row of rows) expect(NEIGHBORHOOD_TYPES).toContain(row.type_code);
});

it("분기를 생략하면 최신 분기와 같고, 다른 분기는 값이 달라진다 (결정적)", async () => {
  const latest = await (await call()).json();
  const pinned = await (await call("?year_quarter=20262")).json();
  const older = await (await call("?year_quarter=20251")).json();
  expect(latest).toEqual(pinned);
  expect(older).not.toEqual(latest);
});

it("단일 프로필 라우트와 같은 유형을 준다 (두 계약의 원천이 하나)", async () => {
  const { GET: single } = await import("../[regionCode]/route");
  const rows = await (await call()).json();
  const first = rows[0];
  const profile = await (
    await single(new Request(`http://test/api/mock/profiles/${first.region_code}`), {
      params: Promise.resolve({ regionCode: first.region_code }),
    })
  ).json();
  expect(profile.neighborhood_type).toBe(first.type_code);
});
