import { expect, it } from "vitest";
import { GET } from "./route";

it("로그인 수단은 { google: boolean } 형태다", async () => {
  const res = await GET();
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ google: true });
});
