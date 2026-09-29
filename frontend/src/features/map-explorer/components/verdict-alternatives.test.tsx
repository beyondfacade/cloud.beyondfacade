import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { VerdictAlternatives as Alternatives } from "@/shared/api/types";
import { ApiError } from "@/shared/api/client";
import * as api from "../api";
import { VerdictAlternatives } from "./verdict-alternatives";

const BOTH: Alternatives = {
  region_code: "1168064000", industry_id: "korean_food", neighborhood_type: "office",
  industries: [
    { industry_id: "snack", industry_name: "분식", verdict_code: "clear", strong_count: 0, on_count: 0 },
    { industry_id: "pub", industry_name: "호프·주점", verdict_code: "orange", strong_count: 0, on_count: 1 },
  ],
  regions: [
    { region_code: "1168059000", region_name: "삼성2동", verdict_code: "clear", strong_count: 0, on_count: 0 },
  ],
};

function renderAlternatives(industry = "korean_food") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <VerdictAlternatives regionCode="1168064000" industry={industry} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

it("동네 고정·업종 고정 두 줄을 이름과 판정 라벨로 보여준다", async () => {
  vi.spyOn(api, "fetchVerdictAlternatives").mockResolvedValue(BOTH);
  renderAlternatives();
  const industries = await screen.findByTestId("alt-industries");
  expect(industries).toHaveTextContent("굳이 이 동네라면");
  expect(industries).toHaveTextContent("분식");
  expect(industries).toHaveTextContent("경고 없음");
  expect(industries).toHaveTextContent("호프·주점");
  expect(industries).toHaveTextContent("조건부");
  const regions = screen.getByTestId("alt-regions");
  expect(regions).toHaveTextContent("굳이 한식이라면");
  expect(regions).toHaveTextContent("삼성2동");
  expect(regions).toHaveTextContent("낮 인구 우위형"); // 같은 동네 유형 안에서 골랐다는 단서
});

it("한 축만 있으면 그 줄만, 둘 다 비면 아무것도 그리지 않는다", async () => {
  const spy = vi.spyOn(api, "fetchVerdictAlternatives").mockResolvedValue({ ...BOTH, regions: [] });
  renderAlternatives();
  expect(await screen.findByTestId("alt-industries")).toBeInTheDocument();
  expect(screen.queryByTestId("alt-regions")).toBeNull();

  spy.mockResolvedValue({ ...BOTH, industries: [], regions: [] });
  const { container } = renderAlternatives("cafe");
  await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(container.firstChild).toBeNull());
});

it("404·오류는 조용히 비운다 (카드 본체가 이미 있으므로 안내문 없음)", async () => {
  const spy = vi.spyOn(api, "fetchVerdictAlternatives").mockRejectedValue(new ApiError("VERDICT_NOT_FOUND", "없음"));
  const { container } = renderAlternatives();
  await waitFor(() => expect(spy).toHaveBeenCalled());
  await waitFor(() => expect(container.firstChild).toBeNull());
  expect(screen.queryByRole("alert")).toBeNull();
});
