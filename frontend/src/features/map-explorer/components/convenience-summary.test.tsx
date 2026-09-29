import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ConvenienceRegionSummary } from "@/shared/api/types";
import { ConvenienceSummarySection } from "./convenience-summary";

function renderSummary(summary: ConvenienceRegionSummary) {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(summary)));
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <ConvenienceSummarySection regionCode="1168064000" />
  </QueryClientProvider>);
}

afterEach(() => vi.unstubAllGlobals());

it("편의점 수와 원천 기준월만 한 줄로 표시한다", async () => {
  renderSummary({ region_code: "1168064000", store_count: 149, brands: [{ brand: "GS25", count: 54 }], source_stdr_ym: "202606" });
  expect(await screen.findByText("편의점 149곳 · 기준 2026년 6월")).toBeInTheDocument();
  expect(screen.queryByRole("list")).toBeNull();
});

it("기준월이 없으면 편의점 수만 표시한다", async () => {
  renderSummary({ region_code: "1168064000", store_count: 2, brands: [], source_stdr_ym: null });
  expect(await screen.findByText("편의점 2곳")).toBeInTheDocument();
});

it("편의점이 없으면 안내 문구만 보여준다", async () => {
  renderSummary({ region_code: "1168064000", store_count: 0, brands: [], source_stdr_ym: null });
  expect(await screen.findByText("편의점이 없습니다.")).toBeInTheDocument();
});
