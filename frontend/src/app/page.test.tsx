import { render, screen } from "@testing-library/react";
import Home from "./page";

it("이전 지도 주소의 선택값을 보존하여 지도 경로로 이동한다", async () => {
  const result = Promise.resolve().then(() => Home({ searchParams: Promise.resolve({
    region: "1168064000", industry: "cafe", year: "2025",
  }) }));
  await expect(result).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/map?region=1168064000&industry=cafe&year=2025;307;",
  });
});

it("반복된 검색값과 특수문자도 지도 주소에 보존한다", async () => {
  const result = Promise.resolve().then(() => Home({ searchParams: Promise.resolve({
    metric: "", region: ["1168064000", "1168065000"], note: "서울 & 카페", absent: undefined,
  }) }));
  await expect(result).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/map?metric=&region=1168064000&region=1168065000&note=%EC%84%9C%EC%9A%B8+%26+%EC%B9%B4%ED%8E%98;307;",
  });
});

it.each([{}, { utm_source: "newsletter" }])("지도 선택값이 없는 방문에는 탐색 시작 링크를 제공한다 (%j)", async (query) => {
  render(await Home({ searchParams: Promise.resolve(query) }));
  expect(screen.getByRole("link", { name: "상권 탐색하기" })).toHaveAttribute("href", "/map");
});
