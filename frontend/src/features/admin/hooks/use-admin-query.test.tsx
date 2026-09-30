import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/client";
import * as api from "../api";
import { useAdminMe } from "./use-admin-query";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/admin/security",
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => {
  vi.restoreAllMocks();
  replace.mockReset();
});

it("세션이 만료되면(401) 지금 경로를 next로 실어 로그인으로 보낸다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockRejectedValue(new ApiError("UNAUTHENTICATED", "로그인 필요"));
  renderHook(() => useAdminMe(), { wrapper });
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?next=%2Fadmin%2Fsecurity"));
});

it("권한 부족(403) 같은 다른 오류는 로그인으로 보내지 않는다", async () => {
  vi.spyOn(api, "fetchAdminMe").mockRejectedValue(new ApiError("FORBIDDEN_ROLE", "권한 없음"));
  const { result } = renderHook(() => useAdminMe(), { wrapper });
  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(replace).not.toHaveBeenCalled();
});
