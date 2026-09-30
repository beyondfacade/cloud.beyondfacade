import { beforeEach, expect, it, vi } from "vitest";

const apiGet = vi.fn();
vi.mock("@/shared/api/client", () => ({ apiGet: (path: string) => apiGet(path), apiPost: vi.fn() }));

const { fetchFundingCandidates } = await import("./api");

beforeEach(() => apiGet.mockReset().mockResolvedValue({ candidates: [] }));

it("후보 공고는 동을 함께 보내 다른 구 전용 공고를 빼고 받는다", async () => {
  await fetchFundingCandidates("korean_food", 30_000_000, "pre", "1162052500");
  const params = new URLSearchParams(apiGet.mock.calls[0][0].split("?")[1]);
  expect(apiGet.mock.calls[0][0]).toMatch(/^\/funding\/candidates\?/);
  expect(params.get("region")).toBe("1162052500");
  expect(params.get("industry")).toBe("korean_food");
});

it("동을 모르면 동 없이 보낸다", async () => {
  await fetchFundingCandidates(null, null, "pre", null);
  expect(apiGet.mock.calls[0][0]).toBe("/funding/candidates?stage=pre");
});
