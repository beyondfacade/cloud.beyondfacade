import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { RegionProfile } from "@/shared/api/types";
import { NeighborhoodLine } from "./neighborhood-line";

const profile: RegionProfile = {
  region_code: "1168064000", year_quarter: "20262", neighborhood_type: "office", type_reason: "직장인구가 상주인구의 5.9배",
  time_label: "day", peak_block: "day", trough_block: "night", worker_resident_ratio: 5.9, weekend_index: 0.7,
  night_index: 0.64, footfall_20s_share: 0.22, fnb_share: 0.016, facility_total: 542, resident_total: 34082,
  block_intensities: { morning: 0.974, day: 1.4, evening: 1.138, night: 0.687 },
};

function renderLine() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return { client, ...render(
    <QueryClientProvider client={client}>
      <NeighborhoodLine regionCode="1168064000" />
    </QueryClientProvider>,
  ) };
}

afterEach(() => vi.unstubAllGlobals());

it("최신 분기 프로필의 유형과 시간대 문장을 한 줄에 표시하고 분류 이유를 툴팁으로 제공한다", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: string) => {
    const url = new URL(input, "http://localhost");
    // 분기를 지정하면 최신 프로필을 받지 못하는 API 경계를 고정한다.
    return Response.json(url.pathname.endsWith("/profiles/1168064000") && !url.search
      ? profile : { error: { code: "REGION_PROFILE_NOT_FOUND", message: "자료 없음" } }, { status: url.search ? 404 : 200 });
  }));
  renderLine();
  expect(await screen.findByText("낮 인구 우위형 · 점심·오후가 하루의 정점")).toHaveAttribute("title", "직장인구가 상주인구의 5.9배");
});

it("시간대 자료가 없으면 유형 이름만 표시한다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ...profile, time_label: null })));
  renderLine();
  expect(await screen.findByTitle(profile.type_reason)).toHaveTextContent(/^낮 인구 우위형$/);
});

it.each([404, 500])("프로필을 받지 못한 %s 응답에서는 줄 자체를 그리지 않는다", async (status) => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ error: { code: "REGION_PROFILE_NOT_FOUND", message: "자료 없음" } }, { status })));
  const { container, client } = renderLine();
  await waitFor(() => expect(client.getQueryState(["region-profile", "1168064000", null])?.status).toBe("error"));
  expect(container).toBeEmptyDOMElement();
});

it("프로필을 불러오는 동안 줄을 그리지 않는다", () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
  expect(renderLine().container).toBeEmptyDOMElement();
});
